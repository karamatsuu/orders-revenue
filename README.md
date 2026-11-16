# Orders Revenue Report

A small Python script that parses an order log (`orders.csv`), skips and reports
invalid rows, and prints **revenue per customer per month, sorted by revenue**.

No third-party dependencies — just the Python standard library (Python 3.9+).

## Input format

A CSV with a header row and these columns:

| Column       | Meaning                               |
|--------------|---------------------------------------|
| `order_id`   | Unique order identifier               |
| `customer_id`| Customer identifier                   |
| `amount`     | Order amount (non-negative number)    |
| `created_at` | Order timestamp                       |

Supported `created_at` formats include `2026-01-05 10:22:00`,
`2026-02-10T16:45:00Z`, `2026-01-05`, `2026/03/01`, and `DD/MM/YYYY`.

## Usage

```bash
python revenue_report.py                 # reads ./orders.csv
python revenue_report.py path/to/orders.csv
python revenue_report.py orders.csv --report-file errors.txt
```

The revenue table is printed to **stdout**. The report of skipped rows goes to
**stderr** by default (or to a file with `--report-file`), so you can separate
the two:

```bash
python revenue_report.py orders.csv > report.txt 2> errors.txt
```

## What counts as an invalid row

A row is skipped (and reported with its line number and reason) when:

- a required column is missing or empty (`order_id`, `customer_id`);
- `amount` is empty, non-numeric, or negative;
- `created_at` cannot be parsed as a date.

Amounts are parsed with `Decimal` to avoid floating-point rounding errors.

## Example

Running against the included sample `orders.csv`:

```
Invalid-row report:
  line 6 (order_id=1005): amount is not a number: ''
  line 8 (order_id=1007): empty customer_id
  line 9 (order_id=1008): amount is not a number: 'abc'
  line 11 (order_id=1010): negative amount: '-20.00'
  line 13 (order_id=1012): unrecognized date format: 'not-a-date'

Skipped 5 invalid row(s); kept 10.
customer_id  month         revenue
----------------------------------
C003         2026-03        519.99
C001         2026-02        310.00
C003         2026-02        200.00
C001         2026-01        165.75
C002         2026-02        150.75
C002         2026-01         89.00
C001         2026-03         75.00
C002         2026-03         60.00
```

## Project layout

```
.
├── revenue_report.py   # the script
├── orders.csv          # sample input (valid + deliberately invalid rows)
└── README.md
```
