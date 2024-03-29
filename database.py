from sqlalchemy import String, Integer, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, mapped_column
from sqlalchemy_utils import database_exists, create_database,ChoiceType

engine = create_engine("sqlite:///instance/bib.db", echo=True)

if not database_exists("sqlite:///instance/bib.db"):
    create_database(engine.url)

Base = declarative_base()

class Gebruiker(Base):

    rol = [
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
    rol = mapped_column(ChoiceType(rol,impl=String()))
   
class Rol(Base):
    __tablename__ = "Rol"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    naam = mapped_column(String)

class Gebruiker_rol(Base):
    __tablename__ = "Gerbuiker_rol"

    rol_id = mapped_column(Integer, ForeignKey('Gebruiker.id'), primary_key=True)
    gebruiker_id = mapped_column(Integer, ForeignKey('Rol.id'), primary_key=True)


class Boeken(Base):
    __tablename__ = "Boeken"

    bkn_ISBN = mapped_column(String, primary_key=True)
    bkn_genre = mapped_column(String)
    bkn_thema = mapped_column(String)
    bkn_auteur = mapped_column(String)


Base.metadata.create_all(bind=engine)
