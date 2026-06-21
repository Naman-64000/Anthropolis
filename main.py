import argparse
import sys
from simulation.core.engine import SimulationEngine
from simulation.utils.helpers import format_report_summary, get_default_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stochastic City Simulation: Virtual Urban Laboratory"
    )
    defaults = get_default_config()

    parser.add_argument(
        "--ticks",
        type=int,
        default=180,
        help="Number of ticks (months) to run the simulation (default: 180)",
    )
    parser.add_argument(
        "--pop",
        type=int,
        default=defaults["population_size"],
        help=f"Initial population size (default: {defaults['population_size']})",
    )
    parser.add_argument(
        "--gov",
        type=float,
        default=defaults["initial_gov_capital"],
        help=f"Initial government treasury balance (default: {defaults['initial_gov_capital']})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=defaults["seed"],
        help=f"Random seed for reproducibility (default: {defaults['seed']})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="mospi_national_accounts_2024_2039.csv",
        help="Filename to save the historical metrics CSV (default: mospi_national_accounts_2024_2039.csv)",
    )

    args = parser.parse_args()

    print(f"Initializing Virtual Urban Laboratory...")
    print(f"Population: {args.pop} | Gov Capital: ${args.gov:.2f} | Seed: {args.seed}")

    engine = SimulationEngine(
        population_size=args.pop,
        initial_gov_capital=args.gov,
        seed=args.seed,
    )

    print(f"Running simulation for {args.ticks} ticks...")
    
    # Progress indicator
    milestone = max(1, args.ticks // 10)
    for t in range(args.ticks):
        engine.step()
        if (t + 1) % milestone == 0 or (t + 1) == args.ticks:
            pct = ((t + 1) / args.ticks) * 100
            alive_count = len([c for c in engine.citizens if not c.is_dead])
            print(f"  Progress: {pct:3.0f}% | Day {engine.tick_count} | Alive Population: {alive_count}")

    # Generate output
    df = engine.get_history_dataframe()
    df.to_csv(args.output, index=False)
    print(f"Time-series macro metrics successfully exported to: {args.output}")

    # Print final summary
    final_metrics = engine.history[-1]
    report = format_report_summary(final_metrics)
    print(report)


if __name__ == "__main__":
    main()
