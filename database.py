from sqlalchemy import Table, Column, String, Integer, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, mapped_column
from sqlalchemy_utils import database_exists, create_database, ChoiceType

engine = create_engine("sqlite:///instance/bib.db", echo=True)

if not database_exists("sqlite:///instance/bib.db"):
    create_database(engine.url)

Base = declarative_base()

boek_thema_association = Table(
    'boek_thema_association', Base.metadata,
    Column('boek_id', Integer, ForeignKey('boek.ISBN')),
    Column('thema_id', Integer, ForeignKey('thema.id'))
)

boek_genre_association = Table(
    'boek_genre_association', Base.metadata,
    Column('boek_id', Integer, ForeignKey('boek.ISBN')),
    Column('genre_id', Integer, ForeignKey('genre.id'))
)

boek_auteur_association = Table(
    'boek_auteur_association', Base.metadata,
    Column('boek_id', Integer, ForeignKey('boek.ISBN')),
    Column('auteur_id', Integer, ForeignKey('auteur.id'))
)

class Gebruiker(Base):

    rol_list = [
            ('bibliothecaris','Bibliothecaris'),
            ('ontlener','Ontlener')
           ]
    
    __tablename__ = "Gebruiker"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String)
    achternaam = mapped_column(String)
    email = mapped_column(String)
    paswoord = mapped_column(String)
    geboortedtm = mapped_column(String)
    tel_nr = mapped_column(Integer)
    rol = mapped_column(ChoiceType(rol_list,impl=String()))
   



class Boek(Base):
    __tablename__ = "boek"

    ISBN = mapped_column(String, primary_key=True)
    titel = mapped_column(String, unique=True, nullable=False)

    themas = relationship('Thema', secondary=boek_thema_association, back_populates='boeken')
    genres = relationship('Genre', secondary=boek_genre_association, back_populates='boeken')
    auteurs = relationship('Auteur', secondary=boek_auteur_association, back_populates='boeken')

class Genre(Base):
    __tablename__ = "genre"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String)

    boeken = relationship('Boek', secondary=boek_genre_association, back_populates='genres')

class Thema(Base):
    __tablename__ = "thema"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String)

    boeken = relationship('Boek', secondary=boek_thema_association, back_populates='themas')

class Auteur(Base):
    __tablename__ = "auteur"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String)

    boeken = relationship('Boek', secondary=boek_auteur_association, back_populates='auteurs')

Base.metadata.create_all(bind=engine)
