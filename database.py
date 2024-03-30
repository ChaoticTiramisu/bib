from sqlalchemy import String, Integer, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, mapped_column
from sqlalchemy_utils import database_exists, create_database,ChoiceType

engine = create_engine("sqlite:///instance/bib.db", echo=True)

if not database_exists("sqlite:///instance/bib.db"):
    create_database(engine.url)

Base = declarative_base()

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
   
class Rol(Base):
    __tablename__ = "Rol"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String)

class Gebruiker_rol(Base):
    __tablename__ = "Gerbuiker_rol"

    rol_id = mapped_column(Integer, ForeignKey('Gebruiker.id'), primary_key=True)
    gebruiker_id = mapped_column(Integer, ForeignKey('Rol.id'), primary_key=True)


class Boek(Base):
    __tablename__ = "boek"

    ISBN = mapped_column(String, primary_key=True)
    titel = mapped_column(String, unique=True, nullable=False)
    thema_id = mapped_column(Integer, ForeignKey('thema.id'), nullable=False)
    auteur_id = mapped_column(Integer, ForeignKey('auteur.id'), nullable=False)
    genre_id = mapped_column(Integer, ForeignKey('genre.id'), nullable=False)
   
    #relaties
    genre = relationship('Genre', back_populates='boek')
    thema = relationship('Thema', back_populates='boek')
    auteur = relationship('Auteur', back_populates='boek')
class Genre(Base):
    __tablename__ = "genre"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    genre = mapped_column(String)
   
    #relaties
    boek = relationship('Boek', back_populates='genre')

class Thema(Base):
    __tablename__ = "thema"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    thema = mapped_column(String)
   
    #relaties
    boek = relationship('Boek', back_populates='thema')

class Auteur(Base):
    __tablename__ = "auteur"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    auteur = mapped_column(String)
  
    #relaties
    boek = relationship('Boek', back_populates='auteur')

Base.metadata.create_all(bind=engine)
