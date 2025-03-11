# het importen van verschilde zaken voor sqlalchemy (database)
from sqlalchemy import Table, Column, String, Integer, ForeignKey, create_engine, Boolean
from sqlalchemy.orm import relationship, declarative_base, mapped_column
from sqlalchemy_utils import database_exists, create_database, ChoiceType

# start het programma die de database aanmaakt dit is in een instance folder met de naam van de database is bib. echo is debugging informatie weergeven
engine = create_engine("sqlite:///instance/bib.db", echo=True)

# indien de database nog niet bestaat, zal hij deze aanmaken en als hij al bestaat zal hij het niet runnen.
if not database_exists("sqlite:///instance/bib.db"):
    create_database(engine.url)

# lange variable korter maken, voor sneller gebruik
Base = declarative_base()

# associatie(apparte tabel waar thema en boek worden gelinkt), metadata zijn gegevens die altijd moeten ingevuld worden
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

# een klasse dat gebruikt heet, dit zijn de echte tabellen met de gebruikers erin en hun nodig kolomen
class Gebruiker(Base):
# rol_list zijn de rollen die bestaan, en zodat de gebruiker enkel zijn eigen rol kan gebruiken.
    rol_list = [
            ('admin', 'Admin'),
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
    titel = mapped_column(String, nullable=False)
    gereserveerd = mapped_column(Boolean,default=False)
    status = mapped_column(Boolean, nullable=False)
    beschrijving = mapped_column(String, nullable=False )
    bvdm = mapped_column(Boolean, nullable=True)

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

# alle data wordt toegevoegd aan het databasebestand = alle data worden erin gedaan (altijd nodig)
Base.metadata.create_all(bind=engine)
