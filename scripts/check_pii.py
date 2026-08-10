from app.core.pii import decrypt_pii, encrypt_pii


def main() -> None:
    sample = "12 George Street"
    encrypted = encrypt_pii(sample)
    decrypted = decrypt_pii(encrypted)

    print("Encrypted sample:")
    print(encrypted)
    print("Decrypted sample:")
    print(decrypted)


if __name__ == "__main__":
    main()
