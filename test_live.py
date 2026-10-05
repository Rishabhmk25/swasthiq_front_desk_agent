import requests
import json
import sys

def test_live_site(api_url):
    print(f"Testing live API at: {api_url}")
    
    # Payload designed to trigger a clinical escalation (chest pain)
    payload = {
        "conversation_id": "test_live_001",
        "turns": [
            {
                "speaker": "caller",
                "text": "Hi, I have been having severe chest pain for the last hour. I need to see a doctor immediately."
            }
        ]
    }
    
    try:
        response = requests.post(f"{api_url}/agent/run", json=payload)
        if response.status_code == 200:
            print("✅ Success! Sent a clinical emergency test to the live agent.")
            print("Response:", json.dumps(response.json(), indent=2))
            print("\n👉 Now, go to your Vercel website and refresh the Handoff Queue. You should see a red 'CLINICAL' escalation popup!")
        else:
            print(f"❌ Failed. Status Code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    url = input("Enter your Render backend URL (e.g., https://swasthiq.onrender.com): ").strip()
    # Remove trailing slash if accidentally added
    if url.endswith("/"):
        url = url[:-1]
    if url:
        test_live_site(url)
    else:
        print("URL cannot be empty.")
