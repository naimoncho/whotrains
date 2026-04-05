from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.sql import func
from database import Base
 
class User(Base):
    __tablename__ = "users"
 
    id               = Column(Integer, primary_key=True, index=True)
    strava_id        = Column(String, unique=True, index=True)
    email            = Column(String, unique=True, index=True)
    name             = Column(String)
    profile_pic      = Column(String, nullable=True)
    access_token     = Column(String)
    refresh_token    = Column(String)
    token_expires_at = Column(Integer)
    is_pro           = Column(Boolean, default=False)
    ntfy_channel     = Column(String, nullable=True)
    fc_max           = Column(Integer, default=202)
    weight_kg        = Column(Float, nullable=True)
    height_cm        = Column(Float, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
 
class Analysis(Base):
    __tablename__ = "analyses"
 
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, index=True)
    content    = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
 