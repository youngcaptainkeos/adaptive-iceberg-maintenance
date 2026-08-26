CREATE DATABASE IF NOT EXISTS ${catalog}.${database};
CREATE TABLE IF NOT EXISTS ${catalog}.${database}.smoke_table (id INT, name STRING) USING iceberg;
