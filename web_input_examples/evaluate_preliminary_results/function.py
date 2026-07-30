def evaluate_experiment(experiment_id):
    import random

    # The flow that calls this example Globus Compute function
    # expects these keys to exist.
    return {
        "experiment_id": experiment_id,
        "experiment_runtime": 120,
        "measured_db": random.choice([5, 10, 75]),
        "histogram_skew": random.randint(1, 100),
        "confidence_pct": random.randint(80, 97),
    }
