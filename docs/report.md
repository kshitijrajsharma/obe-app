# Open Building Extractor — Report

This report describes my application. It explains what the app does in my code, what problem I was trying to solve and what I did.

## 1. State of the Art

There are several widely used public sources of building footprints:

- **Google Open Buildings**: AI-detected building polygons released in open batches
- **Microsoft Building Footprints**: Large AI-derived building polygons published in tiles
- **Overture Maps (Buildings)**: Consolidated partner and community data under a common schema
- **OpenStreetMap (OSM)**: Community-mapped data; coverage and detail vary by place

Today, comparing these sources for a specific area often requires downloading regional files or many tiles, calling bbox-based APIs, and running spatial operations to see overlaps and gaps. A simple no‑code flow for “draw area → fetch from all sources → see layers → get basic stats → export” is useful for many users. This application provides that flow.

## 2. Problem statement

Multiple public building datasets exist for the same geography, but coverage is uneven, access methods differ (tile indexes versus bbox APIs), and getting only a user’s area of interest (AOI) with basic comparisons usually needs spatial processing.

The problem is to make it straightforward for any user to assess completeness and consistency of building footprints in a user‑defined AOI by fetching from Google, Microsoft, Overture, and OSM, visualizing them together, computing basic stats, and producing GIS‑friendly exports.

## 3. Objective / Question

### Objective

Build a no‑code web app where a user defines an AOI on a map and receives:

- Building footprints from Google, Microsoft, Overture, and OSM for that AOI
- A side‑by‑side visualization with simple layer controls
- A small table of stats that shows per‑source coverage and overlaps
- Exports in GIS‑friendly formats that the user can download and share

### Core Question

Within the selected AOI, how complete are the building footprints across these sources, where do they overlap, and where are the gaps?

## 4. Method

### 4.1 Stack

- **Backend**: Django with PostGIS
- **Frontend**: Django template HTML with vanilla JS and Tailwind CSS
- **Map rendering**: MapLibre GL
- **Drawing tools**: Terradraw on top of MapLibre GL for AOI capture

### 4.2 AOI Capture

- The user draws a rectangle or polygon on the map using Terradraw
- The geometry is sent to the backend and stored for the extract
- When needed, a GeoJSON bbox is derived from the AOI for bbox‑based sources

### 4.3 Data Acquisition (by source)
- Google Open Buildings
  - Uses a provider‑published tile/index structure.
  - The backend computes which tiles intersect the AOI and fetches only those tiles.

- Microsoft Building Footprints
  - Uses a published tile/index structure.
  - The backend computes intersecting tiles for the AOI and fetches those tiles.

- Overture Maps (Buildings)
  - Accepts a GeoJSON bbox request.
  - The backend derives a bbox from the AOI, requests features from the Overture endpoint, then clips to the AOI.

- OpenStreetMap (Buildings)
  - Uses the OSM raw data API with a GeoJSON bbox derived from the AOI.
  - The backend filters to buildings and clips to the AOI.

Notes
- Tile‑based sources (Google, Microsoft) are pulled via intersecting tile lists computed from the AOI.
- Bbox‑based sources (Overture, OSM) are requested with the AOI’s bbox; exact AOI clipping is applied afterward.

### 4.4 Spatial Processing and Stats

- **Storage**: Incoming features are stored in PostGIS
- **Clipping**: Features are clipped to the exact AOI polygon (not just the bbox)
- **Normalization**: Minimal attributes are kept consistent for rendering and export (source and geometry, plus basic fields as available)
- **Basic stats**:
  - Per‑source building counts within the AOI
  - Total footprint area per source
  - Overlap indicators between sources using spatial intersects (for example, count of features from Source A that intersect any feature from Source B)
- **Deduplication**: For tile boundaries (Google and Microsoft), duplicates are handled so the same building is not double‑counted

### 4.5 Visualization and Interaction

- Each source is rendered as its own layer in MapLibre GL with distinct colors and transparency
- Layer toggles allow quick visual comparison of coverage and agreement
- A tabular panel shows counts, areas, and overlap indicators alongside the map

### 4.6 Exports

- The application produces downloadable, GIS‑friendly exports of the AOI subset
- Exports include building geometries and basic attributes per source
- Users can share the exported files with others

### 4.7 End‑to‑End Flow

1. The user draws an AOI with Terradraw (or provides GeoJSON)
2. The backend:
   - Computes tile intersections (Google, Microsoft) and bboxes (Overture, OSM)
   - Fetches the data per source
   - Loads data into PostGIS and clips to the AOI
   - Computes basic stats and prepares exports
3. The frontend:
   - Displays layers on the map
   - Shows the stats table
   - Provides export downloads

## 5. Results

### Delivered Capabilities

- A no‑code extractor for building footprints across Google, Microsoft, Overture, and OSM for any user‑drawn AOI
- One map view with per‑source layers to compare coverage visually
- A compact stats table that reports per‑source counts, total areas, and overlap indicators within the AOI
- GIS‑friendly exports that users can download and share

### Example Use Cases

- **City scan**: Draw a polygon around a city, see layers together, check counts and overlaps, and download the subset for offline analysis
- **Neighborhood or campus**: Draw a small polygon, confirm where sources agree, identify gaps for editing tasks, and export for field review
- **Rural block**: Draw a rectangle over a rural area, see which sources capture buildings there, examine overlaps, and export the results

### How This Addresses the Problem

- It streamlines pulling from different source mechanisms (tiles versus bbox) for one AOI
- It provides a single view and a consistent set of basic stats to assess completeness
- It outputs data that is ready for standard GIS tools

### Limitations and Notes

- Output reflects each provider's state at request time; providers update on their own schedules
- Bbox requests can include features outside the polygon; clipping to the AOI mitigates this
- Performance and completeness depend on provider availability and AOI size

## Group Member Contributions

This was a solo project.

- **Member**: Me (Kshitij Raj Sharma)
- **Contribution**: 100%

### Work Performed

- **Backend (Django + PostGIS)**: AOI intake; tile‑index intersection for Google and Microsoft; bbox requests for Overture and OSM; clipping; spatial intersects for basic overlap stats; data normalization; export preparation
- **Data fetching scripts**: Implemented tile‑based fetch for Google and Microsoft; implemented bbox‑based fetch for Overture and the OSM raw data API
- **Frontend (vanilla JS + Django templates + Tailwind)**: MapLibre GL integration; Terradraw setup for drawing and editing the AOI; layer toggles; stats panel; wiring to backend endpoints
- **Spatial logic and stats**: Intersections and basic overlap indicators across sources; per‑source counts and total areas inside the AOI; deduplication on tile edges
- **Documentation and testing**: Usage notes; tested different AOI sizes to validate fetching, clipping, stats, and exports


### ScreenShots 

Export Details : 
<img width="1216" height="645" alt="image" src="https://github.com/user-attachments/assets/b252fe17-e790-4e91-a482-0b3e1b1cd4b4" />

Create Export with drawing in Map as well as Upload : 

<img width="1212" height="777" alt="image" src="https://github.com/user-attachments/assets/d5a194ad-461a-492a-85b0-cb01a274fdf0" />

