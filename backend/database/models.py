"""
Database models for PF Intelligence Hub.
Tables: posts, sentiments, polls, poll_responses, provinces, keywords
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class SentimentLabel(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class Platform(str, enum.Enum):
    facebook = "facebook"
    news = "news"
    twitter = "twitter"
    manual = "manual"


class Post(Base):
    """A social media post or news article mentioning Zambian politics / cost of living."""
    __tablename__ = "posts"

    id            = Column(Integer, primary_key=True, index=True)
    external_id   = Column(String(255), unique=True, nullable=True)  # platform's own ID
    platform      = Column(Enum(Platform), nullable=False)
    source_name   = Column(String(255), nullable=False)   # e.g. "Lusaka Times"
    source_url    = Column(String(500), nullable=True)
    content       = Column(Text, nullable=False)
    author        = Column(String(255), nullable=True)
    province      = Column(String(100), nullable=True)    # detected or tagged province
    likes         = Column(Integer, default=0)
    comments      = Column(Integer, default=0)
    shares        = Column(Integer, default=0)
    published_at  = Column(DateTime, nullable=True)
    scraped_at    = Column(DateTime, default=datetime.utcnow)
    is_processed  = Column(Boolean, default=False)

    sentiment     = relationship("Sentiment", back_populates="post", uselist=False)
    post_keywords = relationship("PostKeyword", back_populates="post")


class Sentiment(Base):
    """NLP sentiment analysis result for a post."""
    __tablename__ = "sentiments"

    id             = Column(Integer, primary_key=True, index=True)
    post_id        = Column(Integer, ForeignKey("posts.id"), unique=True)
    label          = Column(Enum(SentimentLabel), nullable=False)
    score          = Column(Float, nullable=False)          # confidence 0.0–1.0
    issues_found   = Column(JSON, default=list)             # ["mealie_meal","fuel",...]
    analysed_at    = Column(DateTime, default=datetime.utcnow)

    post           = relationship("Post", back_populates="sentiment")


class Keyword(Base):
    """Tracked keywords and their issue category."""
    __tablename__ = "keywords"

    id           = Column(Integer, primary_key=True, index=True)
    term         = Column(String(100), unique=True, nullable=False)
    issue        = Column(String(100), nullable=False)   # e.g. "mealie_meal"
    display_name = Column(String(100), nullable=False)   # e.g. "Mealie meal price"
    weight       = Column(Float, default=1.0)            # importance multiplier
    is_active    = Column(Boolean, default=True)

    post_keywords = relationship("PostKeyword", back_populates="keyword")


class PostKeyword(Base):
    """Many-to-many: posts ↔ keywords."""
    __tablename__ = "post_keywords"

    id         = Column(Integer, primary_key=True, index=True)
    post_id    = Column(Integer, ForeignKey("posts.id"))
    keyword_id = Column(Integer, ForeignKey("keywords.id"))

    post       = relationship("Post", back_populates="post_keywords")
    keyword    = relationship("Keyword", back_populates="post_keywords")


class Poll(Base):
    """An opinion poll question."""
    __tablename__ = "polls"

    id           = Column(Integer, primary_key=True, index=True)
    question     = Column(Text, nullable=False)
    is_active    = Column(Boolean, default=True)
    is_public    = Column(Boolean, default=True)   # shown on public site
    created_at   = Column(DateTime, default=datetime.utcnow)
    closes_at    = Column(DateTime, nullable=True)

    options      = relationship("PollOption", back_populates="poll")


class PollOption(Base):
    """A single answer option for a poll."""
    __tablename__ = "poll_options"

    id           = Column(Integer, primary_key=True, index=True)
    poll_id      = Column(Integer, ForeignKey("polls.id"))
    text         = Column(String(500), nullable=False)
    order        = Column(Integer, default=0)

    poll         = relationship("Poll", back_populates="options")
    responses    = relationship("PollResponse", back_populates="option")


class PollResponse(Base):
    """A single voter's response to a poll."""
    __tablename__ = "poll_responses"

    id           = Column(Integer, primary_key=True, index=True)
    poll_id      = Column(Integer, ForeignKey("polls.id"))
    option_id    = Column(Integer, ForeignKey("poll_options.id"))
    province     = Column(String(100), nullable=True)
    age_group    = Column(String(20), nullable=True)    # e.g. "18-25"
    gender       = Column(String(20), nullable=True)
    ip_hash      = Column(String(64), nullable=True)    # hashed to prevent dupes
    responded_at = Column(DateTime, default=datetime.utcnow)

    option       = relationship("PollOption", back_populates="responses")


class ProvinceScore(Base):
    """Daily grievance score snapshot per province."""
    __tablename__ = "province_scores"

    id           = Column(Integer, primary_key=True, index=True)
    province     = Column(String(100), nullable=False)
    score        = Column(Float, nullable=False)         # 0–100
    post_count   = Column(Integer, default=0)
    neg_pct      = Column(Float, default=0.0)
    top_issue    = Column(String(100), nullable=True)
    recorded_at  = Column(DateTime, default=datetime.utcnow)
