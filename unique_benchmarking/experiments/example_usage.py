#!/usr/bin/env python3
"""
Example usage of the experiment CLI
"""

# Example 1: Using the CLI directly
print("Example CLI usage:")
print("python cli.py --assistant-ids assistant_1 assistant_2 assistant_3 \\")
print("              --user-id user123 \\")
print("              --company-id company456 \\")
print(
    "              --queries 'What is machine learning?' 'How does AI work?' 'Explain neural networks' \\"
)
print("              --golden-model gpt-4")

print("\n" + "=" * 60 + "\n")

# Example 2: Using the ExperimentRunner class programmatically
print("Example programmatic usage:")
print("""
from cli import ExperimentRunner

# Create runner
runner = ExperimentRunner()

# Initialize experiment
experiment_id = runner.initialize_experiment(
    assistant_ids=['assistant_1', 'assistant_2', 'assistant_3'],
    user_id='user123',
    company_id='company456',
    queries=[
        'What is machine learning?',
        'How does AI work?',
        'Explain neural networks'
    ]
)

# Run the experiment
stats = runner.run_experiment()
print(f"Completed experiment {experiment_id} with stats: {stats}")
""")
