#By Ryan Grimes 2/27/2026
#Hashes passwords and verifies hashes

from werkzeug.security import generate_password_hash, check_password_hash #Werkzeug handles requests and responses between web servers and .security is the submodule for hashing and data protection.

def hash_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256') #Hashes the password using the pbkdf2:sha256 algorithm

def verify_password(hashed_password, password): 
    return check_password_hash(hashed_password, password) #Compares hash of inputted password to hash of storred password for that username