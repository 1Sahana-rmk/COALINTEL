from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from database import Base


class MineMaster(Base):
    __tablename__ = "mine_master"

    mine_id = Column(String(100), primary_key=True, index=True)  # Stable ID across financial years
    mine_name = Column(String(150), nullable=False, index=True)
    normalized_mine_name = Column(String(150), nullable=False, index=True)
    original_mine_name = Column(String(150), nullable=True)
    company_name = Column(String(150), nullable=False, index=True)
    parent_company = Column(String(150), nullable=True)
    subsidiary_name = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True, index=True)
    block = Column(String(150), nullable=True)
    coalfield = Column(String(150), nullable=True)
    coal_or_lignite = Column(String(50), default="Coal", nullable=False)
    mine_type = Column(String(50), nullable=True)  # 'OC', 'UG', 'Mixed'
    mining_method = Column(String(100), nullable=True)
    sector = Column(String(50), nullable=True, index=True)  # 'CIL', 'Captive', 'Commercial', 'State PSU', 'NLCIL', 'SCCL', 'Private'
    ownership_type = Column(String(50), nullable=True, index=True)  # 'CIL', 'SCCL', 'Captive', 'Commercial', 'State PSU', 'Private'
    allocation_type = Column(String(50), nullable=True)  # 'Nominated', 'Auctioned', 'Allotted'
    end_use = Column(String(100), nullable=True)  # 'Power', 'Steel', 'Cement', 'Commercial Sale'
    operational_status = Column(String(50), nullable=False, default="PRODUCING", index=True)
    original_status = Column(String(100), nullable=True)  # Preserves raw government wording
    production_status = Column(String(50), nullable=True)
    mine_opening_permission = Column(String(50), nullable=True)
    captive_or_commercial = Column(String(50), nullable=True)
    financial_year = Column(String(20), nullable=True)
    
    # Source provenance & authenticity
    source_id = Column(String(100), nullable=True, index=True)
    source_document = Column(String(200), nullable=True)
    source_url = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_table = Column(String(100), nullable=True)
    source_chapter = Column(String(100), nullable=True)
    source_publication_date = Column(String(50), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    verification_status = Column(String(50), default="UNKNOWN", nullable=True)
    data_origin = Column(String(30), default="UNKNOWN", nullable=True, index=True)


    # Relationships
    aliases = relationship("MineAlias", back_populates="mine", cascade="all, delete-orphan")
    yearly_metrics = relationship("MineYearlyMetric", back_populates="mine", cascade="all, delete-orphan")
    monthly_metrics = relationship("MineMonthlyMetric", back_populates="mine", cascade="all, delete-orphan")
    star_ratings = relationship("StarRating", back_populates="mine", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MineMaster(id='{self.mine_id}', name='{self.mine_name}', company='{self.company_name}')>"


class MineAlias(Base):
    __tablename__ = "mine_aliases"

    alias_id = Column(Integer, primary_key=True, autoincrement=True)
    mine_id = Column(String(100), ForeignKey("mine_master.mine_id", ondelete="CASCADE"), nullable=False, index=True)
    original_name = Column(String(150), nullable=False, index=True)
    normalized_name = Column(String(150), nullable=False, index=True)
    source_id = Column(String(100), nullable=True)
    identity_status = Column(String(50), default="verified", nullable=False)  # 'verified', 'needs_review', 'resolved'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    mine = relationship("MineMaster", back_populates="aliases")

    def __repr__(self):
        return f"<MineAlias(id={self.alias_id}, original='{self.original_name}', mine_id='{self.mine_id}')>"


class MineYearlyMetric(Base):
    __tablename__ = "mine_yearly_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mine_id = Column(String(100), ForeignKey("mine_master.mine_id", ondelete="CASCADE"), nullable=False, index=True)
    financial_year = Column(String(20), nullable=False, index=True)  # '2024-25', '2025-26', '2026-27'
    period_type = Column(String(20), default="annual", nullable=False)  # 'annual', 'YTD'
    data_status = Column(String(30), default="final", nullable=False)  # 'final', 'provisional'
    
    # Core Production & Dispatch Metrics in MT (Million Tonnes)
    production_mt = Column(Numeric(14, 4), nullable=True)
    production_target_mt = Column(Numeric(14, 4), nullable=True)
    production_achievement_percent = Column(Numeric(8, 2), nullable=True)
    dispatch_mt = Column(Numeric(14, 4), nullable=True)
    dispatch_target_mt = Column(Numeric(14, 4), nullable=True)
    dispatch_achievement_percent = Column(Numeric(8, 2), nullable=True)
    
    # Mining attributes
    coal_grade = Column(String(50), nullable=True)
    mine_type = Column(String(50), nullable=True)
    mining_method = Column(String(100), nullable=True)
    operational_status = Column(String(50), nullable=True)
    production_status = Column(String(50), nullable=True)
    mine_opening_permission = Column(String(50), nullable=True)
    
    # Star Rating & Environment
    star_rating = Column(Integer, nullable=True)  # 1 to 5, NULL if not available
    star_rating_category = Column(String(50), nullable=True)
    obr_mcum = Column(Numeric(14, 4), nullable=True)  # Overburden Removal in M.Cu.M
    manpower = Column(Integer, nullable=True)
    employment = Column(String(100), nullable=True)

    # Provenance fields
    source_id = Column(String(100), nullable=False, index=True)
    source_document = Column(String(200), nullable=True)
    source_url = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_table = Column(String(100), nullable=True)
    source_published_date = Column(String(50), nullable=True)
    verification_status = Column(String(50), default="verified", nullable=False)  # 'verified', 'provisional', 'unverified'
    quality_status = Column(String(50), default="verified", nullable=False)  # 'verified', 'provisional', 'ytd', 'calculated', 'conflicting', 'partial', 'missing', 'needs_review'
    data_origin = Column(String(30), default="OFFICIAL", nullable=False, index=True)  # 'OFFICIAL', 'calculated', 'demo', 'INTERNAL'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    mine = relationship("MineMaster", back_populates="yearly_metrics")

    __table_args__ = (
        Index("ix_mine_yearly_mine_fy", "mine_id", "financial_year"),
        Index("ix_mine_yearly_fy_origin", "financial_year", "data_origin"),
    )

    def __repr__(self):
        return f"<MineYearlyMetric(mine_id='{self.mine_id}', fy='{self.financial_year}', prod={self.production_mt} MT)>"


class MineMonthlyMetric(Base):
    __tablename__ = "mine_monthly_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mine_id = Column(String(100), ForeignKey("mine_master.mine_id", ondelete="CASCADE"), nullable=False, index=True)
    financial_year = Column(String(20), nullable=False, index=True)  # '2025-26', '2026-27'
    month = Column(String(20), nullable=False, index=True)  # '2026-04', '2026-05', etc.
    period_type = Column(String(20), default="monthly", nullable=False)
    production_mt = Column(Numeric(14, 4), nullable=True)  # NULL = unavailable, 0 = reported 0
    dispatch_mt = Column(Numeric(14, 4), nullable=True)
    target_mt = Column(Numeric(14, 4), nullable=True)
    achievement_percent = Column(Numeric(8, 2), nullable=True)
    data_status = Column(String(30), default="provisional", nullable=False)
    as_of_date = Column(String(30), nullable=True)

    # Provenance
    source_id = Column(String(100), nullable=False)
    source_document = Column(String(200), nullable=True)
    source_url = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_table = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    mine = relationship("MineMaster", back_populates="monthly_metrics")

    __table_args__ = (
        Index("ix_mine_monthly_mine_month", "mine_id", "month"),
    )

    def __repr__(self):
        return f"<MineMonthlyMetric(mine_id='{self.mine_id}', month='{self.month}', prod={self.production_mt})>"


class CoalBlock(Base):
    __tablename__ = "coal_blocks"

    coal_block_id = Column(String(100), primary_key=True, index=True)
    coal_block_name = Column(String(150), nullable=False, index=True)
    mine_name = Column(String(150), nullable=True)
    mine_id = Column(String(100), ForeignKey("mine_master.mine_id", ondelete="SET NULL"), nullable=True, index=True)
    allottee = Column(String(150), nullable=False, index=True)
    company = Column(String(150), nullable=False)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True)
    allocation_method = Column(String(50), nullable=True)  # 'Auction', 'Allotment'
    allocation_date = Column(String(50), nullable=True)
    end_use = Column(String(100), nullable=True)
    sale_of_coal = Column(String(50), nullable=True)
    mine_opening_permission = Column(String(50), nullable=True)
    production_status = Column(String(50), nullable=True, index=True)  # 'PRODUCING', 'UNDER_DEVELOPMENT', 'NON_OPERATIONAL'
    production_mt = Column(Numeric(14, 4), nullable=True)
    target_production_mt = Column(Numeric(14, 4), nullable=True)
    peak_rated_capacity_mtpa = Column(Numeric(14, 4), nullable=True)
    source_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<CoalBlock(id='{self.coal_block_id}', block='{self.coal_block_name}', allottee='{self.allottee}')>"


class StarRating(Base):
    __tablename__ = "star_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mine_id = Column(String(100), ForeignKey("mine_master.mine_id", ondelete="CASCADE"), nullable=False, index=True)
    financial_year = Column(String(20), nullable=False, index=True)
    star_rating = Column(Integer, nullable=True)  # 1 to 5, NULL if not available
    rating_category = Column(String(50), nullable=True)  # '5 Star', '4 Star', etc.
    score_percent = Column(Numeric(6, 2), nullable=True)
    source_id = Column(String(100), nullable=False)
    source_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    mine = relationship("MineMaster", back_populates="star_ratings")

    def __repr__(self):
        return f"<StarRating(mine_id='{self.mine_id}', fy='{self.financial_year}', stars={self.star_rating})>"
