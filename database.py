from sqlalchemy import Table, Column, String, Integer, ForeignKey, create_engine, Boolean, Date, DateTime, Index
from datetime import datetime
from sqlalchemy.orm import relationship, declarative_base, mapped_column, Session
from sqlalchemy_utils import database_exists, create_database, ChoiceType
from werkzeug.security import generate_password_hash

# Initialize the database engine
engine = create_engine("sqlite:///instance/bib.db", echo=True)

# Create the database if it doesn't exist
if not database_exists("sqlite:///instance/bib.db"):
    create_database(engine.url)

# Base class for all models
Base = declarative_base()

# Association tables for many-to-many relationships
boek_thema_association = Table(
    'boek_thema_association', Base.metadata,
    Column('boek_id', String, ForeignKey('boeken.ISBN')),
    Column('thema_id', Integer, ForeignKey('themas.id'))
)

boek_genre_association = Table(
    'boek_genre_association', Base.metadata,
    Column('boek_id', String, ForeignKey('boeken.ISBN')),
    Column('genre_id', Integer, ForeignKey('genres.id'))
)

boek_auteur_association = Table(
    'boek_auteur_association', Base.metadata,
    Column('boek_id', String, ForeignKey('boeken.ISBN')),
    Column('auteur_id', Integer, ForeignKey('auteurs.id'))
)

# User model
class Gebruiker(Base):
    __tablename__ = "gebruikers"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String, nullable=False)
    achternaam = mapped_column(String, nullable=False)
    email = mapped_column(String, nullable=False, unique=True, index=True)
    paswoord = mapped_column(String, nullable=False)
    geboortedtm = mapped_column(Date, nullable=True)
    tel_nr = mapped_column(String, nullable=True)
    actief = mapped_column(Boolean, default=True)
    rol_list = [
        ('admin', 'Admin'),
        ('bibliothecaris', 'Bibliothecaris'),
        ('ontlener', 'Ontlener')
    ]
    rol = mapped_column(ChoiceType(rol_list, impl=String()), nullable=False)

    reservaties = relationship("Reservatie", back_populates="gebruiker", lazy="select")

    def __repr__(self):
        return f"<Gebruiker(id={self.id}, naam={self.naam}, email={self.email}, rol={self.rol})>"

# Book model
class Boek(Base):
    __tablename__ = "boeken"

    ISBN = mapped_column(String, primary_key=True)
    titel = mapped_column(String, nullable=False)
    gereserveerd = mapped_column(Boolean, default=False)
    status = mapped_column(Boolean, nullable=True)
    beschrijving = mapped_column(String, nullable=False)
    bvdm = mapped_column(Boolean, nullable=True)
    toegevoegd_op = mapped_column(DateTime, default=datetime.utcnow)
    aantal = mapped_column(Integer, nullable=False, default=1)
    aantal_bladzijden = mapped_column(Integer, nullable=True)

    themas = relationship('Thema', secondary=boek_thema_association, back_populates='boeken', lazy="select")
    genres = relationship('Genre', secondary=boek_genre_association, back_populates='boeken', lazy="select")
    auteurs = relationship('Auteur', secondary=boek_auteur_association, back_populates='boeken', lazy="select")
    reservaties = relationship("Reservatie", back_populates="boek", lazy="select")

    def __repr__(self):
        return f"<Boek(ISBN={self.ISBN}, titel={self.titel})>"

# Reservation model
class Reservatie(Base):
    __tablename__ = "reservaties"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    boek_isbn = mapped_column(String, ForeignKey("boeken.ISBN"), nullable=False)
    gebruiker_id = mapped_column(Integer, ForeignKey("gebruikers.id"), nullable=False)
    start_date = mapped_column(Date, nullable=False)
    end_date = mapped_column(Date, nullable=False)

    boek = relationship("Boek", back_populates="reservaties", lazy="joined")
    gebruiker = relationship("Gebruiker", back_populates="reservaties", lazy="joined")

    def __repr__(self):
        return f"<Reservatie(id={self.id}, boek_isbn={self.boek_isbn}, gebruiker_id={self.gebruiker_id})>"

# Genre model
class Genre(Base):
    __tablename__ = "genres"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String, nullable=False, unique=True)

    boeken = relationship('Boek', secondary=boek_genre_association, back_populates='genres', lazy="select")

    def __repr__(self):
        return f"<Genre(id={self.id}, naam={self.naam})>"

# Theme model
class Thema(Base):
    __tablename__ = "themas"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String, nullable=False, unique=True)

    boeken = relationship('Boek', secondary=boek_thema_association, back_populates='themas', lazy="select")

    def __repr__(self):
        return f"<Thema(id={self.id}, naam={self.naam})>"

# Author model
class Auteur(Base):
    __tablename__ = "auteurs"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String, nullable=False, unique=True)

    boeken = relationship('Boek', secondary=boek_auteur_association, back_populates='auteurs', lazy="select")

    def __repr__(self):
        return f"<Auteur(id={self.id}, naam={self.naam})>"

# Create all tables
with engine.begin() as connection:
    Base.metadata.create_all(bind=connection)

# Ensure admin account exists
def ensure_admin_account():
    admin_email = "admin@example.com"
    admin_password = "admin123"  # Default password
    with Session(engine) as session:
        # Check if an admin account already exists
        admin = session.query(Gebruiker).filter_by(email=admin_email).first()
        if not admin:
            # Create the admin account
            admin = Gebruiker(
                naam="Admin",
                achternaam="User",
                email=admin_email,
                paswoord=admin_password,  # Securely hash the password
                rol="admin",
                actief=True
            )
            session.add(admin)
            session.commit()
            print(f"Admin account created:\nEmail: {admin_email}\nPassword: {admin_password}")
        else:
            print(f"Admin account already exists:\nEmail: {admin_email}")

# Call the function to ensure the admin account is created
ensure_admin_account()
