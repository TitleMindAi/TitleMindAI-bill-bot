import os

def save_uploaded_file(file_data, filename, save_dir="uploads"):
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)
    with open(filepath, "wb") as f:
        f.write(file_data)
    return filepath