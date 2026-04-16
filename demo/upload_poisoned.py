import os
import sys

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.healer.dify_client import DifyKBClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_poisoned.py <path_to_csv>")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_text = f.read()

    print(f"Uploading {csv_path} directly to Dify without Guardian ETL...")
    
    dataset_id = os.environ.get("DIFY_DATASET_ID")
    if not dataset_id:
        print("ERROR: DIFY_DATASET_ID environment variable is missing.")
        sys.exit(1)
        
    try:
        with DifyKBClient() as client:
            result = client.create_document_by_text(
                dataset_id=dataset_id,
                text=csv_text,
                name="poisoned_direct_import.csv"
            )
            doc = result.get('document', {})
            print(f"SUCCESS! Uploaded poisoned dataset.")
            print(f"Document Name: {doc.get('name')}")
            print(f"Document ID: {doc.get('id')}")
            print("\nYou can now query your Dify Chat App linked to this Knowledge Base to demonstrate LLM Hallucinations.")
    except Exception as exc:
        print(f"Failed to upload: {exc}")

if __name__ == "__main__":
    main()
