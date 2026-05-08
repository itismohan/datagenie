## DataGenie Repository Overview

**DataGenie** is a data governance and metadata management platform built with a **microservices architecture**. Here's what it does:

### Core Functionality

The repository contains multiple specialized APIs organized in the `apps` directory:

1. **Catalog API** - Manages data asset metadata and glossary terms
   - **Assets Service**: Create and list data assets with their properties
   - **Glossary Service**: Manage business glossary terms and definitions

2. **Other APIs** (in the repository structure):
   - **Connector API** - Likely handles data source connections
   - **Lineage API** - Tracks data lineage and relationships
   - **Quality API** - Manages data quality metrics and checks
   - **Search API** - Provides search capabilities across the platform
   - **Frontend** - User interface for the platform

### Technology Stack

- **Backend**: Python with FastAPI (modern, fast web framework)
- **Database**: PostgreSQL for data persistence
- **Architecture**: Microservices pattern with separate API services

### Current State

The repository appears to be in early development, with basic CRUD operations implemented for assets and glossary terms. The in-memory storage in the API routes (dictionaries) suggests this is still a prototype/development version, as production code would use the PostgreSQL database configured in the session.

**Purpose**: DataGenie enables organizations to catalog, govern, and search their data assets while tracking data quality and lineage across their organization.
