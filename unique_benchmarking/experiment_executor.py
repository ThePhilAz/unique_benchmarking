"""
Experiment execution logic for running tests across multiple assistants and questions.
"""

import asyncio
import json
import time
import unique_sdk
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Callable
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion
from logging import getLogger
from schemas import ExperimentResult, ExperimentSummary, Message

logger = getLogger(__name__)


class ExperimentExecutor:
    """Handles the execution of experiments across multiple assistants and questions."""

    def __init__(self, user_id: str, company_id: str, app_id: str, api_key: str):
        """Initialize the experiment executor with configuration."""
        self.user_id = user_id
        self.company_id = company_id
        self.app_id = app_id
        self.api_key = api_key
        self.experiment_directory = None

        # Configure unique_sdk
        unique_sdk.app_id = app_id
        unique_sdk.api_key = api_key
        unique_sdk.api_base = "https://api.uat1.unique.app/public/chat"

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

        # Create directories
        base_path.mkdir(exist_ok=True)
        success_path.mkdir(exist_ok=True)
        error_path.mkdir(exist_ok=True)

        # Save experiment configuration
        config_data = {
            "experiment_id": experiment_dir,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "configuration": {
                "user_id": self.user_id,
                "company_id": self.company_id,
                "app_id": self.app_id,
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
        logger.info(f"  - Config file: {config_file}")

        return str(base_path)

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

        try:
            result = await send_message_and_wait_for_completion(
                user_id=self.user_id,
                company_id=self.company_id,
                assistant_id=assistant_id,
                text=question,
                stop_condition="completedAt",
                max_wait=120,
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

    def run_full_experiment(
        self,
        assistant_ids: List[str],
        questions: List[str],
        progress_callback: Optional[Callable] = None,
    ) -> ExperimentSummary:
        """
        Run the full experiment across all assistant-question combinations.

        Args:
            assistant_ids: List of assistant IDs to test
            questions: List of questions to ask
            progress_callback: Optional callback function for progress updates

        Returns:
            ExperimentSummary with all results
        """
        start_time = datetime.now().isoformat()
        total_tests = len(assistant_ids) * len(questions)
        results = []
        test_counter = 0

        # Create experiment directory structure
        experiment_dir = self.create_experiment_directory(assistant_ids, questions)

        logger.info(
            f"Starting experiment with {len(assistant_ids)} assistants and {len(questions)} questions..."
        )
        logger.info(f"Total tests to run: {total_tests}")

        for assistant_id in assistant_ids:
            for question in questions:
                test_counter += 1

                logger.info(f"\nRunning test {test_counter}/{total_tests}")
                logger.info(f"Assistant: {assistant_id}")
                logger.info(
                    f"Question: {question[:100]}{'...' if len(question) > 100 else ''}"
                )

                # Run the experiment
                message, error, execution_time = self.run_experiment_sync(
                    assistant_id, question
                )
                
                # Create result
                result = ExperimentResult(
                    test_id=test_counter,
                    assistant_id=assistant_id,
                    question=question,
                    success=message is not None,
                    error=error,
                    execution_time=execution_time,
                    timestamp=datetime.now().isoformat(),
                    message=message,
                )

                # Save individual result to appropriate folder
                self.save_individual_result(result)

                results.append(result)

                # Progress callback
                if progress_callback:
                    progress_callback(test_counter, total_tests, result)

                logger.info(f"Result: {'✅ Success' if result.success else '❌ Failed'}")
                logger.info(f"Execution time: {execution_time:.2f}s")

                if error:
                    logger.error(f"Error: {error}")

        # Calculate summary statistics
        completed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - completed_tests
        success_rate = (completed_tests / total_tests) * 100 if total_tests > 0 else 0
        total_execution_time = sum(r.execution_time for r in results)

        summary = ExperimentSummary(
            total_tests=total_tests,
            completed_tests=completed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            total_execution_time=total_execution_time,
            start_time=start_time,
            end_time=datetime.now().isoformat(),
            results=results,
            experiment_directory=experiment_dir,
        )

        # Save summary to experiment directory
        self.save_experiment_summary(summary)

        logger.info("\n🎉 Experiment completed!")
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Successful: {completed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success rate: {success_rate:.1f}%")
        logger.info(f"Total execution time: {total_execution_time:.2f}s")
        logger.info(f"Results saved to: {experiment_dir}")

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
