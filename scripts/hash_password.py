"""Buat hash password admin untuk ADMIN_PASSWORD_HASH: python -m scripts.hash_password"""
import getpass

from app.services.security import hash_password

if __name__ == "__main__":
    pw = getpass.getpass("Password admin: ")
    if pw != getpass.getpass("Ulangi: "):
        raise SystemExit("Tidak sama.")
    print("\nTambahkan ke .env:\nADMIN_PASSWORD_HASH=" + hash_password(pw))
