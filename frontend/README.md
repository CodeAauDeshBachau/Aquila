<<<<<<< HEAD
# Aquila - Flood Monitoring System

A real-time flood monitoring and prediction web application built with Next.js. Aquila provides two powerful modes for flood analysis: **Prediction Mode** for forecasting flood probability and **Detection Mode** for SAR-based satellite flood detection.

![Next.js](https://img.shields.io/badge/Next.js-15.5.4-black)
![React](https://img.shields.io/badge/React-19.1.0-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-38B2AC)

## Features

### 🌊 Dual Monitoring Modes

- **Prediction Mode**: Forecast flood probability using machine learning models with risk assessment, confidence levels, and actionable recommendations
- **Detection Mode**: Analyze SAR (Synthetic Aperture Radar) satellite imagery to detect active flooding

### 🗺️ Interactive Map Interface

- Leaflet-powered interactive map with global coverage
- Pre-defined flood monitoring locations from the Sen1Floods11 dataset (12 global locations)
- Custom location selection by clicking anywhere on the map
- Visual bounding box display for monitoring areas
- Color-coded markers for different location states

### 📊 Real-time Analysis

- Live flood probability calculations
- SAR image visualization with flood detection overlays
- Expandable result panels with detailed analysis
- Full-screen SAR image modal for detailed inspection

### 🌍 Pre-configured Monitoring Locations

The application includes pre-defined monitoring locations covering:
- Bolivia, Colombia, Ghana, India, Cambodia
- Nigeria, Pakistan, Paraguay, Somalia
- Spain, Sri Lanka, USA

## Tech Stack

- **Framework**: Next.js 15.5.4 with App Router
- **UI Library**: React 19.1.0
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4
- **Icons**: Lucide React
- **Maps**: Leaflet (loaded via CDN)

## Project Structure

```
app/
├── components/
│   ├── FloodMap.tsx        # Main map container component
│   ├── Header.tsx          # Application header with controls
│   ├── LocationDropdown.tsx # Location selection dropdown
│   ├── MapInfoPanel.tsx    # Results and info panel
│   ├── MapLegend.tsx       # Map legend component
│   ├── ModeToggle.tsx      # Prediction/Detection mode toggle
│   └── index.ts            # Component exports
├── constants/
│   └── floodLocations.ts   # Pre-defined monitoring locations
├── hooks/
│   └── useFloodMap.ts      # Main map logic and API integration
├── types/
│   └── index.ts            # TypeScript interfaces
├── globals.css             # Global styles
├── layout.tsx              # Root layout
└── page.tsx                # Main application page
```

## Getting Started

### Prerequisites

- Node.js 18.x or later
- npm, yarn, pnpm, or bun

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd aquila
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

3. Create a `.env.local` file for API configuration (optional):
   ```env
   NEXT_PUBLIC_PREDICTION_API_URL=prediction-api-url
   NEXT_PUBLIC_DETECTION_API_URL=detection-api-url
   ```

4. Run the development server:
   ```bash
   npm run dev
   # or
   yarn dev
   # or
   pnpm dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

### Selecting a Location

1. **Dropdown**: Use the location dropdown in the header to select from pre-defined monitoring locations
2. **Map Click**: Click anywhere on the map to set a custom monitoring location
3. **Markers**: Click on existing blue markers to select pre-configured locations

### Monitoring Modes

#### Prediction Mode
- Forecasts flood probability based on location and date
- Provides risk level assessment (Low/Medium/High)
- Displays confidence metrics and recommendations

#### Detection Mode
- Analyzes SAR satellite imagery for flood detection
- Returns visual flood maps with color-coded overlays:
  - Gray: SAR Background
  - Blue: Permanent Water
  - Red: Detected Flood
- Includes date of SAR image capture

### Running Analysis

1. Select a location (from dropdown or map click)
2. Choose the monitoring mode (Prediction/Detection)
3. Click the "Monitor" button
4. View results in the info panel

## API Integration

The application expects backend APIs for flood analysis:

### Prediction API
```
GET /predict/{latitude}/{longitude}/{date}
```
Returns flood probability, risk level, confidence, and recommendations.

### Detection API
```
GET /flood/detect
```
Returns SAR-based flood detection results with base64-encoded flood map images.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms included in the [LICENSE](LICENSE) file.

## Acknowledgments

- [Sen1Floods11 Dataset](https://github.com/cloudtostreet/Sen1Floods11) for flood monitoring location data
- [Leaflet](https://leafletjs.com/) for interactive mapping capabilities
- [Next.js](https://nextjs.org/) for the React framework
=======
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
>>>>>>> 3a770c5bc5f87f2190f13b4d5345a40ca0772360
