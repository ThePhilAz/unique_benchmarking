"""
Django management command for running benchmarking experiments
"""

import uuid
from typing import List, Dict
import asyncio
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueAuth,
    UniqueApp,
    UniqueSettings,
)
from tqdm import tqdm
from unique_toolkit.framework_utilities.openai import get_openai_client
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion
from eval_assistants.management.commands.utils.schema import Message
import unique_sdk
from eval_assistants.models import (
    Configuration,
    Experiment,
    GoldenAnswer,
    AssistantResponse,
)
from logging import getLogger

logger = getLogger(__name__)


class ExperimentRunner:
    """Main class for running benchmarking experiments"""

    def __init__(self):
        self.experiment = None

    def initialize_runner_only(self):
        """Initialize runner configuration without creating a new experiment"""
        self.golden_model = Configuration.get_instance().default_golden_model
        self.app_id = Configuration.get_instance().app_id
        self.api_key = Configuration.get_instance().api_key
        self.base_url = Configuration.get_instance().base_url
        self.timeout = Configuration.get_instance().timeout
        self.user_id = Configuration.get_instance().user_id
        self.company_id = Configuration.get_instance().company_id

        logger.info(
            f"Initializing Unique SDK with user_id: {self.user_id}, company_id: {self.company_id}, app_id: {self.app_id}, api_key: {self.api_key}, base_url: {self.base_url}"
        )
        unique_api = UniqueApi.model_validate(
            {
                "base_url": self.base_url,
            }
        )
        logger.info(f"Initializing Unique Api with base_url: {self.base_url}")
        unique_api = UniqueApi(
            base_url=self.base_url,
        )
        logger.info(f"Initializing Unique Api with base_url: {self.base_url}")
        unique_auth = UniqueAuth.model_validate(
            {
                "user_id": self.user_id,
                "company_id": self.company_id,
            }
        )

        unique_app = UniqueApp.model_validate(
            {
                "app_id": self.app_id,
                "api_key": self.api_key,
                "base_url": self.base_url,
            }
        )
        unique_settings = UniqueSettings(
            auth=unique_auth, app=unique_app, api=unique_api
        )

        unique_sdk.app_id = self.app_id
        unique_sdk.api_key = self.api_key
        unique_sdk.api_base = self.base_url

        self.openai_client = get_openai_client(unique_settings)

    def initialize_experiment(
        self,
        assistant_ids: List[str],
        queries: List[str],
    ) -> str:
        """Initialize a new experiment"""
        experiment_id = f"exp_{uuid.uuid4().hex[:8]}"

        self.golden_model = Configuration.get_instance().default_golden_model
        self.app_id = Configuration.get_instance().app_id
        self.api_key = Configuration.get_instance().api_key
        self.base_url = Configuration.get_instance().base_url
        self.timeout = Configuration.get_instance().timeout
        self.user_id = Configuration.get_instance().user_id
        self.company_id = Configuration.get_instance().company_id

        logger.info(
            f"Initializing Unique SDK with user_id: {self.user_id}, company_id: {self.company_id}, app_id: {self.app_id}, api_key: {self.api_key}, base_url: {self.base_url}"
        )
        unique_api = UniqueApi.model_validate(
            {
                "base_url": self.base_url,
            }
        )
        logger.info(f"Initializing Unique Api with base_url: {self.base_url}")
        unique_api = UniqueApi(
            base_url=self.base_url,
        )
        logger.info(f"Initializing Unique Api with base_url: {self.base_url}")
        unique_auth = UniqueAuth.model_validate(
            {
                "user_id": self.user_id,
                "company_id": self.company_id,
            }
        )
        logger.info(
            f"Initializing Unique Auth with user_id: {self.user_id}, company_id: {self.company_id}"
        )

        unique_app = UniqueApp.model_validate(
            {
                "app_id": self.app_id,
                "api_key": self.api_key,
                "base_url": self.base_url,
            }
        )
        unique_settings = UniqueSettings(
            auth=unique_auth, app=unique_app, api=unique_api
        )

        unique_sdk.app_id = self.app_id
        unique_sdk.api_key = self.api_key
        unique_sdk.api_base = self.base_url

        self.openai_client = get_openai_client(unique_settings)

        self.experiment = Experiment.objects.create(
            experiment_id=experiment_id,
            assistant_ids=assistant_ids,
            user_id=self.user_id,
            company_id=self.company_id,
            queries=queries,
            start_time=timezone.now(),
        )

        return experiment_id

    def get_or_create_golden_answer(
        self, question: str, model_name: str
    ) -> GoldenAnswer:
        """Get existing golden answer or create a new one"""
        question_hash = GoldenAnswer._get_question_hash(question, model_name)

        try:
            # First try to get existing golden answer
            golden_answer = GoldenAnswer.objects.get(question_hash=question_hash)
            logger.info(f"Found existing golden answer for question: {question}")
            return golden_answer
        except GoldenAnswer.DoesNotExist:
            # Golden answer doesn't exist, create a new one
            logger.info(f"Golden answer not found for question {question}, generating new one")
            
            answer, success = self._generate_golden_answer(question)
            
            # Use get_or_create to handle race conditions
            golden_answer, created = GoldenAnswer.objects.get_or_create(
                question_hash=question_hash,
                defaults={
                    'model_name': model_name,
                    'question': question,
                    'answer': answer,
                    'success': success,
                    'started_at': timezone.now(),
                    'ended_at': timezone.now(),
                }
            )
            
            if created:
                logger.info(f"Created new golden answer for question: {question}")
            else:
                logger.info(f"Golden answer was created by another process for question: {question}")
            
            return golden_answer

    def run_assistant_query(
        self, assistant_id: str, question: str
    ) -> AssistantResponse:
        """Run a query against an assistant and store the response"""
        started_at = timezone.now()

        # Interface for assistant query - TO BE IMPLEMENTED
        message, success = self._query_assistant(assistant_id, question)
        references = [ref.model_dump() for ref in message.references]
        ended_at = timezone.now()

        response = AssistantResponse.objects.create(
            experiment=self.experiment,
            question=question,
            chat_id=message.chatId,
            assistant_id=assistant_id,
            answer=message.text,
            processed_answer=message.get_optimized_text(),
            debug_info=message.debugInfo,
            hallucination_level=message.assessment[0].label if message.assessment else None,
            hallucination_reason=message.assessment[0].explanation if message.assessment else None,
            references=references,
            success=success,
            started_at=started_at,
            ended_at=ended_at,
        )

        return response

    def run_experiment(self) -> Dict[str, int]:
        """Run the complete experiment"""
        if not self.experiment:
            raise ValueError(
                "Experiment not initialized. Call initialize_experiment first."
            )

        total_queries = len(self.experiment.queries)
        total_assistants = len(self.experiment.assistant_ids)
        total_tasks = total_queries * total_assistants
        completed_responses = 0
        failed_responses = 0
        task_counter = 0

        # Initialize progress tracking
        self.experiment.initialize_progress(total_tasks)

        try:
            # Create an outer tqdm for questions
            with tqdm(
                self.experiment.queries,
                total=total_queries,
                desc="Questions",
                position=0,
                leave=True,
            ) as question_bar:
                for question_idx, question in enumerate(question_bar):
                    question_bar.set_postfix_str(f"Q: {str(question)[:30]}...")

                    # Update progress for golden answer generation
                    self.experiment.update_progress(
                        current_step=f"Generating golden answer for question {question_idx + 1}/{total_queries}"
                    )

                    # Get or create golden answer
                    logger.info(
                        f"Getting or creating golden answer for question {question}"
                    )
                    golden_answer = self.get_or_create_golden_answer(
                        question, self.golden_model
                    )
                    logger.info(f"Golden answer created: {golden_answer}")

                    # Create an inner tqdm for assistants
                    with tqdm(
                        self.experiment.assistant_ids,
                        total=total_assistants,
                        desc="Assistants",
                        position=1,
                        leave=False,
                    ) as assistant_bar:
                        for assistant_idx, assistant_id in enumerate(assistant_bar):
                            assistant_bar.set_postfix_str(f"Assistant: {assistant_id}")

                            # Update progress for each assistant query
                            task_counter += 1
                            self.experiment.update_progress(
                                completed_tasks=task_counter,
                                current_step=f"Testing assistant {assistant_id} on question {question_idx + 1}/{total_queries} ({task_counter}/{total_tasks})",
                            )

                            logger.info(
                                f"Running query against assistant {assistant_id}"
                            )
                            response = self.run_assistant_query(assistant_id, question)

                            if response.success:
                                completed_responses += 1
                            else:
                                failed_responses += 1

            # Mark experiment as completed
            self.experiment.complete_experiment()

        except Exception as e:
            # Mark experiment as failed if an error occurs
            self.experiment.fail_experiment(str(e))
            raise e

        stats = {
            "total_queries": total_queries,
            "total_assistants": total_assistants,
            "completed_responses": completed_responses,
            "failed_responses": failed_responses,
            "total_responses": completed_responses + failed_responses,
        }

        return stats

    def _generate_golden_answer(self, question: str) -> tuple[str, bool]:
        """Generate a golden answer"""
        success = True
        answer = ""
        try:
            resp = self.openai_client.responses.create(
                model=self.golden_model,
                tools=[{"type": "web_search_preview"}],
                input=question,
                reasoning={"effort": "low"},
            )
            answer = resp.output[-1].content[0].text  # type: ignore
        except Exception as e:
            success = False
            logger.exception(f"Error generating golden answer: {e}")
            answer = f"Error generating golden answer: {e}"

        return answer, success

    def _query_assistant(
        self, assistant_id: str, question: str
    ) -> tuple[Message, bool]:
        """Query an assistant"""
        success = True

        try:
            result = asyncio.run(
                send_message_and_wait_for_completion(
                    user_id=self.user_id,
                    company_id=self.company_id,
                    assistant_id=assistant_id,
                    text=question,
                    stop_condition="completedAt",
                    tool_choices=["WebSearch"],
                    max_wait=self.timeout,
                )
            )
            message = Message.model_validate(result)
            return message, success
        except Exception as e:
            success = False
            message = Message(
                id=str(uuid.uuid4()),
                originalText=question,
                debugInfo={},
                updatedAt=timezone.now().isoformat(),
                stoppedStreamingAt=timezone.now().isoformat(),
                references=[],
                assessment=[],
                chatId=assistant_id,
                text=f"Error querying assistant: {e}",
                createdAt=timezone.now().isoformat(),
                role="assistant",
                completedAt=timezone.now().isoformat(),
            )

        return message, success


class Command(BaseCommand):
    help = "Run benchmarking experiments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--assistant-ids",
            nargs="+",
            required=True,
            help="List of assistant IDs to test",
        )
        parser.add_argument(
            "--user-id", required=True, help="User ID running the experiment"
        )
        parser.add_argument("--company-id", required=True, help="Company ID")
        parser.add_argument(
            "--queries", nargs="+", required=True, help="List of queries to test"
        )
        parser.add_argument(
            "--golden-model",
            default="gpt-4",
            help="Model to use for generating golden answers (default: gpt-4)",
        )

    def handle(self, *args, **options):
        try:
            runner = ExperimentRunner()

            # Initialize experiment
            experiment_id = runner.initialize_experiment(
                assistant_ids=options["assistant_ids"],
                queries=options["queries"],
            )

            self.stdout.write(
                self.style.SUCCESS(f"✓ Initialized experiment: {experiment_id}")
            )
            self.stdout.write(f"  - Assistants: {len(options['assistant_ids'])}")
            self.stdout.write(f"  - Queries: {len(options['queries'])}")
            self.stdout.write(f"  - User: {options['user_id']}")
            self.stdout.write(f"  - Company: {options['company_id']}")

            # Run experiment
            self.stdout.write(f"\n🚀 Starting experiment: {experiment_id}")
            stats = runner.run_experiment()

            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 Experiment {experiment_id} completed!")
            )
            self.stdout.write(f"   Total responses: {stats['total_responses']}")
            self.stdout.write(f"   Successful: {stats['completed_responses']}")
            self.stdout.write(f"   Failed: {stats['failed_responses']}")

        except Exception as e:
            raise CommandError(f"Error running experiment: {e}")
