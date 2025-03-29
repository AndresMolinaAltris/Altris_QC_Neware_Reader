from common.imports import pd, np


def calculate_statistics(features_df, cycle=1):
    """
    Calculate statistics for the specified features across cells for a given cycle.

    Args:
        features_df (pd.DataFrame): DataFrame containing extracted features
        cycle (int): Cycle number to filter data for (default: 1)

    Returns:
        pd.DataFrame: DataFrame containing statistics (mean, std, rsd) for each metric
    """
    # Filter data for the specified cycle
    cycle_data = features_df[features_df['Cycle'] == cycle]

    if cycle_data.empty:
        return None

    # Metrics to calculate statistics for
    metrics = [
        'Specific Charge Capacity (mAh/g)',
        'Specific Discharge Capacity (mAh/g)',
        'Coulombic Efficiency (%)'
    ]

    # Initialize dictionary to store statistics
    stats = {
        'Cell ID': ['Average', 'Std Dev', 'RSD (%)']
    }

    # Calculate statistics for each metric
    for metric in metrics:
        if metric in cycle_data.columns:
            # Get numeric values, ignoring NaN
            values = pd.to_numeric(cycle_data[metric], errors='coerce')

            # Calculate mean and standard deviation
            mean_val = values.mean()
            std_val = values.std()

            # Calculate relative standard deviation (%)
            rsd = (std_val / mean_val * 100) if mean_val != 0 else np.nan

            # Store formatted values
            stats[metric] = [
                f"{mean_val:.1f}",
                f"{std_val:.1f}",
                f"{rsd:.1f}"
            ]
        else:
            # If metric doesn't exist, use placeholders
            stats[metric] = ['-', '-', '-']

    # Convert to DataFrame for easier handling
    stats_df = pd.DataFrame(stats)

    return stats_df