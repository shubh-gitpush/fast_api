from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, joinedload
from sqlalchemy.orm import Session

app = FastAPI()
DATABASE_URL = "sqlite:///./travel.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Database Models
class Itinerary(Base):
    __tablename__ = "itineraries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    nights = Column(Integer)
    days = relationship("Day", back_populates="itinerary")


class Day(Base):
    __tablename__ = "days"
    id = Column(Integer, primary_key=True, index=True)
    day_number = Column(Integer)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"))
    hotel = Column(String)
    transfer = Column(String)
    activities = Column(Text)
    itinerary = relationship("Itinerary", back_populates="days")


Base.metadata.drop_all(bind=engine)  # 👈 This line drops all tables
Base.metadata.create_all(bind=engine)

# ----------------------------#
# Pydantic Schemas
# ----------------------------

class DayCreate(BaseModel):
    day_number: int
    hotel: str
    transfer: str
    activities: str


class ItineraryCreate(BaseModel):
    name: str
    nights: int = Field(..., gt=0)
    days: List[DayCreate]


class DayResponse(DayCreate):
    id: int

    class Config:
        from_attributes = True


class ItineraryResponse(BaseModel):
    id: int
    name: str
    nights: int
    days: List[DayResponse]

    class Config:
        from_attributes = True

# ----------------------------#
# Database Session Dependency
# ----------------------------#

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------#
# API Endpoints
# ----------------------------#

@app.get("/")
def root():
    return {"message": "Travel Itinerary API is running."}

@app.post("/itineraries/", response_model=ItineraryResponse)
def create_itinerary(itinerary: ItineraryCreate, db: Session = Depends(get_db)):
    db_itinerary = Itinerary(name=itinerary.name, nights=itinerary.nights)
    db.add(db_itinerary)
    db.commit()
    db.refresh(db_itinerary)

    for day in itinerary.days:
        db_day = Day(
            day_number=day.day_number,
            hotel=day.hotel,
            transfer=day.transfer,
            activities=day.activities,
            itinerary_id=db_itinerary.id
        )
        db.add(db_day)

    db.commit()
    db.refresh(db_itinerary)
    return db_itinerary

@app.get("/itineraries/{itinerary_id}", response_model=ItineraryResponse)
def read_itinerary(itinerary_id: int, db: Session = Depends(get_db)):
    itinerary = db.query(Itinerary).options(joinedload(Itinerary.days)).filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return itinerary
# recommendation for travel according to nights
@app.get("/recommendations/{nights}", response_model=List[ItineraryResponse])
def recommend_itineraries(nights: int, db: Session = Depends(get_db)):
    itineraries = db.query(Itinerary).filter(Itinerary.nights == nights).all()
    return itineraries

# Seed Data for Dubai
def seed_data():
    db = SessionLocal()

    if db.query(Itinerary).first():
        db.close()
        return  # Already seeded

    # Seed Dubai 3N Tour
    dubai_3n = Itinerary(name="Dubai 3N Tour", nights=3)
    db.add(dubai_3n)
    db.commit()
    db.refresh(dubai_3n)

    days_dubai_3n = [
        Day(day_number=1, hotel="Dubai Hotel A", transfer="Airport to Hotel", activities="Burj Khalifa visit", itinerary_id=dubai_3n.id),
        Day(day_number=2, hotel="Dubai Hotel A", transfer="None", activities="Sky diving", itinerary_id=dubai_3n.id),
        Day(day_number=3, hotel="Dubai Hotel A", transfer="Hotel to Airport", activities="City tour", itinerary_id=dubai_3n.id),
    ]
    db.add_all(days_dubai_3n)
    db.commit()

    # Seed Dubai 2N Tour
    dubai_2n = Itinerary(name="Dubai 2N Tour", nights=2)
    db.add(dubai_2n)
    db.commit()
    db.refresh(dubai_2n)

    days_dubai_2n = [
        Day(day_number=1, hotel="Dubai Resort", transfer="Airport to Resort", activities="Go on a drive", itinerary_id=dubai_2n.id),
        Day(day_number=2, hotel="Dubai Resort", transfer="Resort to Airport", activities="Water sports", itinerary_id=dubai_2n.id),
    ]
    db.add_all(days_dubai_2n)
    db.commit()

    db.close()

# Automatically seed on start
seed_data()


# Sample API Request Format (Documentation)

# POST /itineraries/{itineraries_id}
# Body:
# {
#   "name": "Dubai Combo",
#   "nights": 5,
#   "days": [
#     {"day_number": 1, "hotel": "dubai Hotel", "transfer": "Airport to Hotel", "activities": "Arrival and beach walk"},
#     {"day_number": 2, "hotel": "dubai Hotel", "transfer": "None", "activities": "Island tour"},
#     {"day_number": 3, "hotel": "Transfer Day", "transfer": "Phuket to Krabi", "activities": "Scenic drive"},
#     {"day_number": 4, "hotel": "dubai Resort", "transfer": "None", "activities": "Beach games"},
#     {"day_number": 5, "hotel": "dubai Resort", "transfer": "Hotel to Airport", "activities": "Departure"}
#   ]
# }
