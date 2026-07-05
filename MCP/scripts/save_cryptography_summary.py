import asyncio
from sqlalchemy import select

from db.session import get_db
from db.models.article import ArticleType, ArticleMetadata, ArticleDetails


SUMMARY_TITLE = "Cryptography Fundamentals"
SUMMARY_SOURCE = "https://www.geeksforgeeks.org/computer-networks/cryptography-tutorial/"
SUMMARY_SNIPPET = "Overview of cryptography goals, primitives (symmetric, asymmetric, hashes), common algorithms, modes, and real-world uses."
SUMMARY_CONTENT = '''
Goals: Confidentiality, Integrity, Authentication, Non-repudiation.

Primitives:
- Symmetric encryption: AES (use AEAD modes like GCM or ChaCha20-Poly1305).
- Asymmetric encryption: RSA, ECC (used for key exchange, signatures).
- Hash functions: SHA-2/3 (provide integrity; MD5/SHA1 deprecated).
- MAC / HMAC: keyed integrity (HMAC-SHA256).
- Digital signatures: RSA/ECDSA for authenticity and non-repudiation.
- Key exchange: Diffie-Hellman / ECDH.

Notes: Prefer authenticated encryption; never roll your own crypto; use secure RNGs and proper key sizes; use Argon2/scrypt/bcrypt for password hashing.

Practical exercises: compute file hashes, use OpenSSL to create keys and sign/verify, use Python `cryptography` and `hashlib` for AES-GCM and SHA-256 examples, try TryHackMe "Crypto 101" rooms.
'''


async def save_summary():
    async with get_db() as session:
        # find or create ArticleType
        q = await session.execute(select(ArticleType).where(ArticleType.kind == SUMMARY_TITLE))
        at = q.scalars().first()
        if not at:
            at = ArticleType(kind=SUMMARY_TITLE, description="Fundamentals and practical exercises for cryptography")
            session.add(at)
            await session.flush()

        # create ArticleMetadata
        q2 = await session.execute(
            select(ArticleMetadata).where(ArticleMetadata.link == SUMMARY_SOURCE)
        )
        am = q2.scalars().first()
        if not am:
            am = ArticleMetadata(article_type=at.id, link=SUMMARY_SOURCE, snippet=SUMMARY_SNIPPET, is_populated=True)
            session.add(am)
            await session.flush()

        # create ArticleDetails
        q3 = await session.execute(
            select(ArticleDetails).where(ArticleDetails.metadata_id == am.id)
        )
        ad = q3.scalars().first()
        if not ad:
            ad = ArticleDetails(metadata_id=am.id, content=SUMMARY_CONTENT)
            session.add(ad)
            await session.flush()

        print("Saved cryptography summary to database")


def main():
    asyncio.run(save_summary())


if __name__ == "__main__":
    main()
