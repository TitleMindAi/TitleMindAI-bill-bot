import csv

def write_to_tsv(data_rows, headers, output_path):
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
        writer.writeheader()
        for row in data_rows:
            writer.writerow(row)
    return output_path