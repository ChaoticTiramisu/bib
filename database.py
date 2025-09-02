from flask import app
from sqlalchemy import Table, Column, String, Integer, ForeignKey, create_engine, Boolean, Date, DateTime
from sqlalchemy.orm import relationship, declarative_base, mapped_column, Session
from sqlalchemy_utils import database_exists, create_database, ChoiceType
from datetime import datetime
import sys
import click

# Initialize the database engine
engine = create_engine("postgresql+psycopg2://glorieuxsecundair:wweasyhost_ubuntu_mila_6ICW!@localhost/bibdb", echo=True)

# Create the database if it doesn't exist
if not database_exists(engine.url):
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
    actief = mapped_column(Boolean, default=True)
    rol_list = [
        ('admin', 'Admin'),
        ('bibliothecaris', 'Bibliothecaris'),
        ('ontlener', 'Ontlener')
    ]
    rol = mapped_column(ChoiceType(rol_list, impl=String()), nullable=False)
    deleted = mapped_column(Boolean, default=False)
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
    aantal = mapped_column(Integer, nullable=False, default=1)  # Total copies
    beschikbaar_aantal = mapped_column(Integer, nullable=False, default=1)  # Available copies
    aantal_bladzijden = mapped_column(Integer, nullable=True)
    deleted = mapped_column(Boolean, default=False)
    locatie_id = mapped_column(Integer, ForeignKey("locaties.id"), nullable=True)

    themas = relationship('Thema', secondary=boek_thema_association, back_populates='boeken', lazy="select")
    genres = relationship('Genre', secondary=boek_genre_association, back_populates='boeken', lazy="select")
    auteurs = relationship('Auteur', secondary=boek_auteur_association, back_populates='boeken', lazy="select")
    reservaties = relationship("Reservatie", back_populates="boek", lazy="select")
    locatie = relationship("Locatie", back_populates="boeken")

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
    deleted = mapped_column(Boolean, default=False)
    afgehaald = mapped_column(Boolean, default=False)

    boek = relationship("Boek", back_populates="reservaties", lazy="joined")
    gebruiker = relationship("Gebruiker", back_populates="reservaties", lazy="joined")

    def __repr__(self):
        return f"<Reservatie(id={self.id}, boek_isbn={self.boek_isbn}, gebruiker_id={self.gebruiker_id})>"

# Genre model
class Genre(Base):
    __tablename__ = "genres"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String, nullable=False, unique=True)
    deleted = mapped_column(Boolean, default=False)

    boeken = relationship('Boek', secondary=boek_genre_association, back_populates='genres', lazy="select")

    def __repr__(self):
        return f"<Genre(id={self.id}, naam={self.naam})>"

# Theme model
class Thema(Base):
    __tablename__ = "themas"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String, nullable=False, unique=True)
    deleted = mapped_column(Boolean, default=False)
    boeken = relationship('Boek', secondary=boek_thema_association, back_populates='themas', lazy="select")

    def __repr__(self):
        return f"<Thema(id={self.id}, naam={self.naam})>"

# Author model
class Auteur(Base):
    __tablename__ = "auteurs"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String, nullable=False, unique=True)
    deleted = mapped_column(Boolean, default=False)
    boeken = relationship('Boek', secondary=boek_auteur_association, back_populates='auteurs', lazy="select")

    def __repr__(self):
        return f"<Auteur(id={self.id}, naam={self.naam})>"

# Location model
class Locatie(Base):
    __tablename__ = "locaties"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String, unique=True, nullable=False)
    boeken = relationship("Boek", back_populates="locatie")

# Create all tables
Base.metadata.create_all(engine)

@click.group()
def cli():
    pass

@cli.command("create-admin")
def create_admin():
    admin_email = "admin@example.com"
    admin_password = "admin123"
    with Session(engine) as session:
        admin = session.query(Gebruiker).filter_by(email=admin_email).first()
        if not admin:
            admin = Gebruiker(
                naam="Admin",
                achternaam="User",
                email=admin_email,
                paswoord=admin_password,
                rol="admin",
                actief=True
            )
            session.add(admin)
            session.commit()
            print(f"Admin account created:\nEmail: {admin_email}\nPassword: {admin_password}")
        else:
            print(f"Admin account already exists:\nEmail: {admin_email}")

if __name__ == "__main__":
    cli()

