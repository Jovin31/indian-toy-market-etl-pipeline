# Indian Toy Market ETL Pipeline

Academic group project at BINUS University.

## Overview

This project analyzes Indian toy-market sales data from 2020 to 2024 using a Python ETL workflow, MySQL data warehouse, Apache Airflow orchestration, and Power BI dashboard.

## Technology Stack

- Python and Pandas
- SQLAlchemy and MySQL
- Apache Airflow
- Docker
- Power BI

## Pipeline

1. Load the source CSV into a raw MySQL database.
2. Clean and standardize the data using Python and Pandas.
3. Structure the transformed data into a star-schema warehouse.
4. Orchestrate ingestion and transformation with Apache Airflow.
5. Analyze revenue trends through Power BI.

## Dataset

Indian Toy Market Sales Data (2020–2024):

https://www.kaggle.com/datasets/jayatitrehan/indian-toy-market-sales-data-2020-2024

Download the dataset and place `indian_toy_market_sales_data.csv` inside the `Code` directory.

## Validation Status

The CSV-based transformation dry run processed 100,000 records and built the dimension and fact tables in memory.

The complete MySQL and Airflow pipeline has not yet been revalidated end-to-end in the current environment. Financial data discrepancies are still under review.

## Project Type

Academic group project. Individual contributions should be attributed accurately.
