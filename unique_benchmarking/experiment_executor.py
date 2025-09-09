"""
Experiment execution logic for running tests across multiple assistants and questions.
"""

import asyncio
import re
import json
import time
import unique_sdk
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Callable
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion
from logging import getLogger
from schemas import (
    ExperimentResult,
    ExperimentSummary,
    Message,
    GoldenAnswer,
    QuestionResult,
)
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai import get_openai_client
from dotenv import load_dotenv

load_dotenv()
logger = getLogger(__name__)


class ExperimentExecutor:
    """Handles the execution of experiments across multiple assistants and questions."""

    def __init__(
        self,
        user_id: str,
        company_id: str,
        app_id: str,
        api_key: str,
        base_url: str,
        timeout: int = 120,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize the experiment executor with configuration."""
        self.user_id = user_id
        self.company_id = company_id
        self.app_id = app_id
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.experiment_directory = None

        # Configure OpenAI for golden answer generation
        unique_settings = UniqueSettings.from_env_auto_with_sdk_init()
        self.openai_client = get_openai_client(unique_settings)

        # Configure unique_sdk
        unique_sdk.app_id = app_id
        unique_sdk.api_key = api_key
        unique_sdk.api_base = base_url

    def create_experiment_directory(
        self, assistant_ids: List[str], questions: List[str]
    ) -> str:
        """
        Create experiment directory structure and save configuration.

        Args:
            assistant_ids: List of assistant IDs
            questions: List of questions

        Returns:
            Path to the created experiment directory
        """
        # Create experiments base directory if it doesn't exist
        experiments_base = Path("experiments")
        experiments_base.mkdir(exist_ok=True)

        # Create timestamp-based directory name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_dir = f"experiment_{timestamp}"

        # Create directory structure inside experiments folder
        base_path = experiments_base / experiment_dir
        success_path = base_path / "success"
        error_path = base_path / "error"
        golden_answers_path = base_path / "golden_answers"
        question_rounds_path = base_path / "question_rounds"

        # Create directories
        base_path.mkdir(exist_ok=True)
        success_path.mkdir(exist_ok=True)
        error_path.mkdir(exist_ok=True)
        golden_answers_path.mkdir(exist_ok=True)
        question_rounds_path.mkdir(exist_ok=True)

        # Save experiment configuration
        config_data = {
            "experiment_id": experiment_dir,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "configuration": {
                "user_id": self.user_id,
                "company_id": self.company_id,
                "app_id": self.app_id,
                "timeout": self.timeout,
            },
            "experiment_setup": {
                "assistant_ids": assistant_ids,
                "questions": questions,
                "total_combinations": len(assistant_ids) * len(questions),
            },
            "directory_structure": {
                "base": str(base_path),
                "success": str(success_path),
                "error": str(error_path),
                "golden_answers": str(golden_answers_path),
                "question_rounds": str(question_rounds_path),
            },
        }

        # Save config file
        config_file = base_path / "experiment_config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)

        self.experiment_directory = str(base_path)

        logger.info(f"Created experiment directory: {experiment_dir}")
        logger.info(f"  - Success folder: {success_path}")
        logger.info(f"  - Error folder: {error_path}")
        logger.info(f"  - Golden answers folder: {golden_answers_path}")
        logger.info(f"  - Question rounds folder: {question_rounds_path}")
        logger.info(f"  - Config file: {config_file}")

        return str(base_path)

    async def generate_golden_answer(
        self, question: str, model: str = "litellm:gpt-5"
    ) -> Optional[GoldenAnswer]:
        """
        Generate a golden answer using OpenAI API.

        Args:
            question: The question to generate an answer for
            model: OpenAI model to use (default: gpt-4o-mini)

        Returns:
            GoldenAnswer object or None if generation failed
        """
        try:
            start_time = time.time()
            resp = self.openai_client.responses.create(
                model=model,
                tools=[{"type": "web_search"}],
                input=question,
                reasoning={"effort": "low"},
            )
            generation_time = time.time() - start_time
            return GoldenAnswer(
                question=question,
                answer=resp.output[-1].content[0].text,  # type: ignore
                model=model,
                timestamp=datetime.now().isoformat(),
                generation_time=generation_time,
            )
        except Exception as e:
            logger.error(f"Error generating golden answer: {e}")
            return None

    def save_golden_answer(
        self, golden_answer: GoldenAnswer, question_id: int
    ) -> str | None:
        """
        Save golden answer to the experiment directory.

        Args:
            golden_answer: The golden answer to save
            question_id: The question ID for filename

        Returns:
            Path to saved file or None if failed
        """
        if not self.experiment_directory:
            logger.warning("No experiment directory set")
            return None

        base_path = Path(self.experiment_directory)
        golden_answers_dir = base_path / "golden_answers"
        golden_answers_dir.mkdir(exist_ok=True)

        filename = f"golden_answer_q{question_id}.json"
        filepath = golden_answers_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(golden_answer.model_dump(), f, indent=2)

            logger.info(f"Saved golden answer to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving golden answer to {filepath}: {e}")
            return None

    def save_individual_result(self, result: ExperimentResult) -> str | None:
        """
        Save individual test result to appropriate folder.

        Args:
            result: The experiment result
            message: The message object (if successful)

        Returns:
            Path to saved file or None if failed
        """
        if not self.experiment_directory:
            print("Warning: No experiment directory set")
            return None

        base_path = Path(self.experiment_directory)

        # Determine folder based on success/failure
        if result.success and result.message:
            folder = base_path / "success"
            chat_id = result.message.chatId
        else:
            folder = base_path / "error"
            chat_id = f"failed_test_{result.test_id}"

        # Create filename using chat_id
        filename = f"{chat_id}.json"
        filepath = folder / filename

        # Prepare data to save
        save_data = result.model_dump()

        try:
            with open(filepath, "w") as f:
                json.dump(save_data, f, indent=2)

            logger.info(f"Saved result to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.exception(f"Error saving result to {filepath}: {e}")
            return None

    async def run_single_experiment(
        self, assistant_id: str, question: str
    ) -> Tuple[Message | None, str | None, float]:
        """
        Run a single experiment with one assistant and one question.

        Args:
            assistant_id: The assistant ID to test
            question: The question to ask

        Returns:
            Tuple of (Message result, error message, execution time)
        """
        start_time = time.time()
        match = re.search(r"\((.*?)\)", question)
        restrict_date = None
        search_query = question
        if match:
            restrict_date = match.group(1)
            
        if restrict_date:
            search_query = question.replace(f"({restrict_date})", "")

        text = f"Answer the following question: {question}. Please use the following search query for the web search: {search_query}."
        if restrict_date:
            text += f"\nUse the restrict date: {restrict_date} for the web search."

        try:
            result = await send_message_and_wait_for_completion(
                user_id=self.user_id,
                company_id=self.company_id,
                assistant_id=assistant_id,
                text= text,
                stop_condition="completedAt",
                tool_choices=["WebSearch"],
                max_wait=self.timeout,
            )

            message = Message.model_validate(result)
            message.optimize_text()
            execution_time = time.time() - start_time

            return message, None, execution_time

        except Exception as e:
            execution_time = time.time() - start_time
            return None, str(e), execution_time

    def run_experiment_sync(
        self, assistant_id: str, question: str
    ) -> Tuple[Message | None, str | None, float]:
        """Synchronous wrapper for running a single experiment."""
        return asyncio.run(self.run_single_experiment(assistant_id, question))

    def process_question_round(
        self,
        question: str,
        question_id: int,
        assistant_ids: List[str],
        progress_callback: Optional[Callable] = None,
    ) -> QuestionResult:
        """
        Process one complete round for a single question:
        1. Get golden answer (placeholder)
        2. Run question on all assistants
        3. Aggregate results and save to file

        Args:
            question: The question to ask
            question_id: The question ID for tracking
            assistant_ids: List of assistant IDs to test
            progress_callback: Optional callback function for progress updates

        Returns:
            QuestionResult with aggregated results
        """
        logger.info(f"\n🔄 Round {question_id}: Processing Question")
        logger.info(f"Question: {question[:100]}{'...' if len(question) > 100 else ''}")

        # Step 1: Get golden answer (placeholder)
        logger.info("1️⃣ Getting golden answer...")
        golden_answer = asyncio.run(self.generate_golden_answer(question))

        if golden_answer:
            self.save_golden_answer(golden_answer, question_id)
            logger.info("✅ Golden answer obtained")
        else:
            logger.info("⚠️ Golden answer not available (placeholder)")

        # Step 2: Iterate question over all assistants
        logger.info(f"2️⃣ Testing question on {len(assistant_ids)} assistants...")
        assistant_results = []

        for i, assistant_id in enumerate(assistant_ids, 1):
            logger.info(
                f"   Testing assistant {i}/{len(assistant_ids)}: {assistant_id}"
            )

            # Run the experiment
            message, error, execution_time = self.run_experiment_sync(
                assistant_id, question
            )

            # Create result
            result = ExperimentResult(
                test_id=(question_id - 1) * len(assistant_ids) + i,
                assistant_id=assistant_id,
                question=question,
                success=message is not None,
                error=error,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
                message=message,
            )

            # Save individual result to success/error folders
            self.save_individual_result(result)
            assistant_results.append(result)

            # Progress callback
            if progress_callback:
                total_tests = len(assistant_ids) * question_id  # Estimate for progress
                progress_callback(result.test_id, total_tests, result)

            logger.info(
                f"   {'✅' if result.success else '❌'} {assistant_id}: {execution_time:.2f}s"
            )

        # Step 3: Aggregate results under one object
        successful_assistants = sum(1 for r in assistant_results if r.success)
        failed_assistants = len(assistant_results) - successful_assistants
        success_rate = (
            (successful_assistants / len(assistant_results) * 100)
            if assistant_results
            else 0
        )
        total_execution_time = sum(r.execution_time for r in assistant_results)

        question_result = QuestionResult(
            question_id=question_id,
            question=question,
            golden_answer=golden_answer,
            assistant_results=assistant_results,
            total_assistants=len(assistant_ids),
            successful_assistants=successful_assistants,
            failed_assistants=failed_assistants,
            success_rate=success_rate,
            total_execution_time=total_execution_time,
        )

        # Step 4: Save the round results to file
        self.save_question_round_results(question_result)

        logger.info(
            f"✅ Round {question_id} completed: {successful_assistants}/{len(assistant_ids)} succeeded ({success_rate:.1f}%)"
        )

        return question_result

    def save_question_round_results(
        self, question_result: QuestionResult
    ) -> str | None:
        """
        Save the results of one question round to a file.

        Args:
            question_result: The aggregated question result

        Returns:
            Path to saved file or None if failed
        """
        if not self.experiment_directory:
            logger.warning("No experiment directory set")
            return None

        base_path = Path(self.experiment_directory)
        rounds_dir = base_path / "question_rounds"
        rounds_dir.mkdir(exist_ok=True)

        filename = f"question_round_{question_result.question_id}.json"
        filepath = rounds_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(question_result.model_dump(), f, indent=2)

            logger.info(f"💾 Round results saved to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving round results to {filepath}: {e}")
            return None

    def run_full_experiment(
        self,
        assistant_ids: List[str],
        questions: List[str],
        progress_callback: Optional[Callable] = None,
    ) -> ExperimentSummary:
        """
        Run the simplified experiment:
        For each question in the dataset, repeat the 4-step process.

        Args:
            assistant_ids: List of assistant IDs to test
            questions: List of questions to ask
            progress_callback: Optional callback function for progress updates

        Returns:
            ExperimentSummary with all results
        """
        start_time = datetime.now().isoformat()
        total_tests = len(assistant_ids) * len(questions)

        # Create experiment directory structure
        experiment_dir = self.create_experiment_directory(assistant_ids, questions)

        logger.info("\n🚀 Starting Simplified Question-Round Experiment")
        logger.info(f"Dataset size: {len(questions)} questions")
        logger.info(f"Assistants per question: {len(assistant_ids)}")
        logger.info(f"Total tests: {total_tests}")

        question_results = []
        all_results = []  # For backward compatibility

        # Repeat for all questions in the dataset
        for question_id, question in enumerate(questions, 1):
            logger.info(f"\n📝 Processing Question {question_id}/{len(questions)}")

            # Process one complete round for this question
            question_result = self.process_question_round(
                question, question_id, assistant_ids, progress_callback
            )

            question_results.append(question_result)
            all_results.extend(question_result.assistant_results)

        # Calculate final summary statistics
        completed_tests = sum(1 for r in all_results if r.success)
        failed_tests = total_tests - completed_tests
        success_rate = (completed_tests / total_tests) * 100 if total_tests > 0 else 0
        total_execution_time = sum(r.execution_time for r in all_results)

        summary = ExperimentSummary(
            total_tests=total_tests,
            completed_tests=completed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            total_execution_time=total_execution_time,
            start_time=start_time,
            end_time=datetime.now().isoformat(),
            results=all_results,
            question_results=question_results,
            experiment_directory=experiment_dir,
        )

        # Save final summary
        self.save_experiment_summary(summary)

        logger.info("\n🎉 Experiment Completed!")
        logger.info(f"✅ {len(questions)} question rounds processed")
        logger.info(
            f"✅ {sum(1 for qr in question_results if qr.golden_answer is not None)} golden answers obtained"
        )
        logger.info(
            f"✅ {completed_tests}/{total_tests} tests successful ({success_rate:.1f}%)"
        )
        logger.info(f"✅ Total execution time: {total_execution_time:.2f}s")
        logger.info(f"📁 Results saved to: {experiment_dir}")

        return summary

    def save_experiment_summary(self, summary: ExperimentSummary) -> str:
        """
        Save experiment summary to the experiment directory.

        Args:
            summary: The experiment summary to save

        Returns:
            The filename where summary was saved
        """
        if not self.experiment_directory:
            logger.warning("Warning: No experiment directory set")
            return ""

        base_path = Path(self.experiment_directory)
        summary_file = base_path / "experiment_summary.json"

        # Convert to dictionary for JSON serialization
        data = summary.model_dump()

        with open(summary_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Experiment summary saved to: {summary_file}")
        return str(summary_file)

    def save_results(
        self, summary: ExperimentSummary, filename: str | None = None
    ) -> str:
        """
        Save experiment results to a JSON file (legacy method, use save_experiment_summary instead).

        Args:
            summary: The experiment summary to save
            filename: Optional filename (auto-generated if not provided)

        Returns:
            The filename where results were saved
        """
        # If experiment directory exists, use the summary method instead
        if self.experiment_directory:
            return self.save_experiment_summary(summary)

        # Fallback to old method if no experiment directory
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_results_{timestamp}.json"

        # Convert to dictionary for JSON serialization
        data = summary.model_dump()

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Results saved to: {filename}")
        return filename
