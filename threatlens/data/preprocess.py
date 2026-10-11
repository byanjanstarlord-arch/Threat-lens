"""
ThreatLens AI - CLI Preprocessing & Partitioning Tool
python -m threatlens.data.preprocess
"""

from threatlens.data.pipeline import process_raw_dataset_to_clean_parquet, build_dual_track_partitions

def main():
    print("=" * 60)
    print("THREATLENS AI - DATASET PREPROCESSING & PARTITIONING")
    print("=" * 60)
    clean_parquet = process_raw_dataset_to_clean_parquet()
    build_dual_track_partitions(clean_parquet)

if __name__ == "__main__":
    main()
