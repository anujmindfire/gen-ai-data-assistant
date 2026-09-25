"""Pydantic schemas for SQL database reflection and schema metadata."""

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Schema metadata definition for a single database column."""

    name: str = Field(..., description="Column name")
    type: str = Field(
        ..., description="Data type representation (e.g. INTEGER, VARCHAR)"
    )
    nullable: bool = Field(
        default=True, description="Whether column permits NULL values"
    )
    primary_key: bool = Field(
        default=False, description="Whether column is part of primary key"
    )
    default: str | None = Field(default=None, description="Default value or expression")


class RelationshipSchema(BaseModel):
    """Foreign key relationship metadata connecting two database tables."""

    from_table: str = Field(..., description="Source table name containing foreign key")
    from_column: str = Field(..., description="Source column name")
    to_table: str = Field(..., description="Referenced target table name")
    to_column: str = Field(..., description="Referenced target column name")
    constraint_name: str | None = Field(
        default=None, description="Foreign key constraint identifier"
    )


class TableSchema(BaseModel):
    """Schema metadata representation for a single database table."""

    name: str = Field(..., description="Table name")
    columns: list[ColumnSchema] = Field(
        default_factory=list, description="List of table columns"
    )
    primary_keys: list[str] = Field(
        default_factory=list, description="List of primary key column names"
    )
    foreign_keys: list[RelationshipSchema] = Field(
        default_factory=list,
        description="List of outgoing foreign key constraints",
    )


class DatabaseSchema(BaseModel):
    """Complete database schema representation including tables and relationships."""

    database_name: str = Field(..., description="Target database identifier/name")
    tables: list[TableSchema] = Field(
        default_factory=list, description="Array of database table schemas"
    )
    relationships: list[RelationshipSchema] = Field(
        default_factory=list,
        description="Array of detected foreign key relationships",
    )
    inspected_at: str = Field(
        ..., description="ISO 8601 timestamp of schema inspection"
    )
