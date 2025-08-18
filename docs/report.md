# Open Building Extractor : Report

This report describes my application. It explains what the app does in my code, what problem I was trying to solve and what I did.

## 1. State of the Art

There are several widely used public sources of building footprints:

- **Google Open Buildings**: AI-detected building polygons released in open batches
- **Microsoft Building Footprints**: Large AI-derived building polygons published in tiles
- **Overture Maps (Buildings)**: Consolidated partner and community data under a common schema
- **OpenStreetMap (OSM)**: Community-mapped data; coverage and detail vary by place

Today, accessing these sources often requires technical knowledge of each provider's API, data formats, and processing requirements. Users need to understand tile systems, coordinate transformations, and data formats to extract building footprints for their specific areas. This creates a barrier for many users who simply want building data for their area of interest.

## 2. Problem statement

Multiple public building datasets exist for the same geography, but accessing and comparing them requires technical knowledge of each source's API, data formats, and processing requirements. Users need a simple way to extract building footprints from multiple sources for their specific area of interest without dealing with the technical complexity of each data provider.

The problem is to provide a user-friendly web interface that simplifies building data extraction from Google Open Buildings, Microsoft Building Footprints, Overture Maps, and OpenStreetMap for any user-defined area.

## 3. Objective / Question

### Objective

Build a web application with a REST API backend that allows users to:

- Define an area of interest (AOI) by drawing a polygon on an interactive map
- Select building data sources (Google, Microsoft, Overture, OSM) and output formats
- Process extraction requests asynchronously in the background
- Download extracted building footprints in standard GIS formats (GeoParquet, GeoJSON, Shapefile, GeoPackage)

### Core Question

How can we simplify the process of extracting building footprints from multiple public data sources for any user-defined area without requiring technical expertise?

## 4. Method

### 4.1 Stack

- **Backend**: Django REST API with PostGIS for spatial data storage
- **Data processing**: OBE (Open Building Extractor) Python library
- **Task queue**: Huey for asynchronous export processing
- **Authentication**: JWT tokens using Django REST Framework Simple JWT
- **Frontend**: Single-page web application using vanilla JavaScript and Tailwind CSS
- **Map interface**: MapLibre GL with MapboxDraw for polygon drawing

### 4.2 Application Architecture

The application is structured as a REST API backend with a simple web frontend. Users authenticate via JWT tokens and can create export requests that are processed asynchronously using a task queue.

### 4.3 AOI Capture

- Users draw polygons on a web map using MapboxDraw controls integrated with MapLibre GL
- The polygon geometry is captured as GeoJSON and sent to the Django backend via REST API
- Area of Interest polygons are stored in PostGIS as geometry fields in the Export model

### 4.4 Data Processing

The application leverages the existing OBE (Open Building Extractor) library for data acquisition:

- **Google Open Buildings**: AI-detected building polygons
- **Microsoft Building Footprints**: Large-scale AI-derived building data with optional country filtering
- **OpenStreetMap Buildings**: Community-mapped building data
- **Overture Buildings**: Consolidated building data from multiple partners

The OBE library handles the technical complexity of accessing each data source, including different API methods, tile systems, and data formats.

### 4.5 Export Processing

- **Asynchronous processing**: Export requests are queued using Huey task queue to handle long-running operations
- **Background tasks**: The `process_export` task uses the OBE library to fetch building data for the specified AOI and selected sources
- **Statistics generation**: Basic statistics are computed including building counts and total areas per source
- **Multiple output formats**: Exported data is saved in user-selected formats (GeoParquet, GeoJSON, Shapefile, GeoPackage)
- **File management**: Completed exports are stored as downloadable files with metadata tracking

### 4.6 User Interface

The frontend provides a simple interface for export management:

- **Interactive map**: Users draw areas of interest using drawing tools on a MapLibre GL map
- **Export configuration**: Forms for selecting data sources, output formats, and providing export metadata
- **Authentication**: Login and registration system for user account management
- **Export dashboard**: Users can view their export history, check processing status, and download completed files
- **Public sharing**: Optional public sharing of exports for collaboration

### 4.7 REST API Endpoints

The application exposes RESTful API endpoints for:

- **Authentication**: User registration, login, and JWT token management
- **Export management**: CRUD operations for export configurations
- **Export runs**: Creating and monitoring export processing jobs
- **File downloads**: Serving completed export files
- **Utilities**: AOI validation and source configuration schemas

### 4.8 End‑to‑End Flow

1. User authenticates and accesses the web interface
2. User draws a polygon on the map to define their area of interest
3. User configures export settings (sources, formats, metadata)
4. Export request is submitted and queued for processing
5. Background task processes the export using the OBE library
6. User receives notification when export is complete and can download results

## 5. Results

### Delivered Capabilities

- A REST API backend that wraps the OBE library for simplified building data extraction
- A web interface for drawing areas of interest and configuring export requests
- Asynchronous processing of export requests to handle large datasets
- Multiple output format support for compatibility with GIS software
- User authentication and export management system

### How This Addresses the Problem

- It provides a simple web interface that requires no technical knowledge to extract building data
- It handles the complexity of different data source APIs behind a unified interface
- It supports multiple output formats for compatibility with various workflows
- It processes requests asynchronously to handle large areas without blocking the interface

### Limitations and Notes

- Data quality and coverage depend on the underlying data sources
- Processing time varies based on area size and selected data sources
- The application requires the OBE library to be properly configured for data source access
- Export file sizes can be large for areas with dense building coverage

## Group Member Contributions

This was a solo project.

- **Member**: Me (Kshitij Raj Sharma)
- **Contribution**: 100%

### Work Performed

- **Backend development**: Implemented Django REST API with authentication, export models, and task processing
- **Database design**: Created PostGIS-enabled models for storing AOI geometries and export metadata
- **Task processing**: Integrated Huey task queue for asynchronous export processing using the OBE library
- **Frontend development**: Built single-page web application with MapLibre GL for interactive map and export management
- **API integration**: Connected frontend to backend REST endpoints for user authentication and export operations
- **File management**: Implemented export file storage and download functionality
- **Testing and validation**: Tested export functionality with different area sizes and data source combinations

### ScreenShots 

Export Details : 
<img width="1216" height="645" alt="image" src="https://github.com/user-attachments/assets/b252fe17-e790-4e91-a482-0b3e1b1cd4b4" />

Create Export with drawing in Map as well as Upload : 

<img width="1212" height="777" alt="image" src="https://github.com/user-attachments/assets/d5a194ad-461a-492a-85b0-cb01a274fdf0" />

Results : 
<img width="1211" height="758" alt="image" src="https://github.com/user-attachments/assets/af2e3e9e-a00a-4b5f-a890-72e880731be8" />

<img width="657" height="285" alt="image" src="https://github.com/user-attachments/assets/121d567b-049d-428e-9d94-dd33572ae4a1" />

