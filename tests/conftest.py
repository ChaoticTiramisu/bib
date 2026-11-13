"""Pytest-configuratie: gebruik een tijdelijke database, nooit instance/bib.db."""

import os
import tempfile

TEST_DIR = tempfile.mkdtemp(prefix="bib-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DIR, 'test.db')}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["FLASK_DEBUG"] = "0"

import pytest  # noqa: E402
from flask_bcrypt import generate_password_hash  # noqa: E402

import app as app_module  # noqa: E402
from database import Base, Gebruiker, Session, engine  # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture()
def client():
    with Session(engine) as session:
        if not session.query(Gebruiker).filter_by(email="test@example.com").first():
            session.add(
                Gebruiker(
                    naam="Test",
                    achternaam="Gebruiker",
                    email="test@example.com",
                    paswoord=generate_password_hash("test123").decode("utf-8"),
                    rol="admin",
                    actief=True,
                )
            )
            session.commit()

    with app_module.app.test_client() as test_client:
        yield test_client
