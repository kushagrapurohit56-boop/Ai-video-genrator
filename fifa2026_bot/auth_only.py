import os
from google_auth_oauthlib.flow import InstalledAppFlow

def get_youtube_client():
    YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    
    print("Opening browser for authentication...")
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json", YOUTUBE_SCOPES
    )
    creds = flow.run_local_server(port=0)
    
    # Save the credentials for the next run
    with open("token.pickle", "wb") as token:
        import pickle
        pickle.dump(creds, token)
        
    print("\n✅ SUCCESS! token.pickle saved. You are fully authenticated!")

if __name__ == "__main__":
    get_youtube_client()
