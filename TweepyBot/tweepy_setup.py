import tweepy
import os

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
baerer_token = os.getenv("BAERER_TOKEN")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

# Initialisierung des Tweepy Clients mit den Zugangsdaten für die Twitter API.
# Dieser Client wird verwendet, um Anfragen an die Twitter API v2 Endpunkte zu senden,
# die OAuth 2.0 Bearer Token für die Authentifizierung nutzen.
client = tweepy.Client(baerer_token, api_key, api_secret, access_token, access_token_secret)

# Einrichtung der OAuth1a-Authentifizierung, die für Benutzerkontextoperationen wie
# das Veröffentlichen eines Tweets erforderlich ist. Dies verwendet den OAuth 1.0a Benutzerkontext,
# der alle vier Schlüssel und Geheimnisse benötigt.
auth = tweepy.OAuthHandler(api_key, api_secret)
auth.set_access_token(access_token, access_token_secret)

# Das api-Objekt ermöglicht den Zugriff auf das volle Spektrum der Twitter RESTful-Methoden.
api = tweepy.API(auth)

# Erstellen und Senden eines Tweets mit dem Text "rando". Der Tweet wird sofort bei Ausführung gesendet.
# Hinweis: Stellen Sie sicher, dass die bereitgestellten Anmeldeinformationen die erforderlichen Berechtigungen haben,
# um Tweets zu posten.
try:
    client.create_tweet(text="rando")
except tweepy.TweepyException as e:
    print(f"Es ist ein Fehler aufgetreten: {e}")
