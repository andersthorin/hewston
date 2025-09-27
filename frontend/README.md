# Hewston Frontend

**React TypeScript frontend for the Hewston backtesting platform**

This is the web interface for Hewston, providing interactive visualization of backtesting results with real-time playback, comprehensive charts, and intuitive controls.

## 🚀 Features

- **Interactive Charts**: TradingView Lightweight Charts for candlestick and equity visualization
- **Real-Time Streaming**: WebSocket integration for live backtest playback
- **Type-Safe API**: Full TypeScript coverage with Zod validation
- **Modern UI**: TailwindCSS with responsive design
- **Performance Optimized**: Imperative chart APIs and Web Workers for smooth streaming

## 🛠 Tech Stack

- **React 19** with TypeScript and strict mode
- **Vite** for fast development and building
- **TailwindCSS** for utility-first styling
- **TanStack Query** for server state management
- **Zod** for runtime type validation
- **TradingView Lightweight Charts** for financial visualization
- **React Router** for client-side routing

## 📋 Prerequisites

- **Node.js 22.x** or later
- **npm** package manager
- **Backend server** running on http://127.0.0.1:8000

## 🚀 Quick Start

### Development Server
```bash
npm install
npm run dev
```
The app will be available at http://127.0.0.1:5173

### Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server with HMR |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint for code quality |
| `npm run test` | Run Vitest test suite |
| `npm run type-check` | Run TypeScript compiler check |

## 🏗 Architecture

### Component Structure
```
src/
├── components/          # Presentational components
│   ├── ChartOHLC.tsx   # Candlestick chart with imperative API
│   ├── EquityChart.tsx # Equity curve visualization
│   ├── RunsTable.tsx   # Backtest runs table
│   ├── FiltersBar.tsx  # Filtering controls
│   └── PlaybackControls.tsx # Play/pause/speed controls
├── containers/         # Data-connected containers
│   ├── RunsListContainer.tsx # Runs list with data fetching
│   └── RunPlayerContainer.tsx # Playback with WebSocket
├── views/              # Route-level views
│   └── RunDetail.tsx   # Individual run detail page
├── services/           # API and data services
│   ├── api.ts         # REST API client with Zod validation
│   ├── ws.ts          # WebSocket hook for streaming
│   └── transport.ts   # HTTP utilities
├── hooks/              # Custom React hooks
├── types/              # TypeScript definitions
├── workers/            # Web Workers for performance
└── utils/              # Helper functions
```

### Design Principles

#### Separation of Concerns
- **Presentational Components**: Pure UI components with no side effects
- **Containers**: Handle data fetching, state management, and business logic
- **Services**: Encapsulate API communication and external integrations

#### Type Safety
- **Strict TypeScript**: No `any` types in production code
- **Zod Validation**: Runtime type checking at API boundaries
- **Interface Contracts**: Clear type definitions for all component props

#### Performance
- **Imperative Chart APIs**: Direct chart manipulation for high-frequency updates
- **Web Workers**: Stream parsing off the main thread
- **React Query**: Intelligent caching and background updates

## 🔌 API Integration

### REST API
```typescript
// Fetch backtest runs
const runs = await listBacktests({
  symbol: 'AAPL',
  limit: 20,
  offset: 0
});

// Get run details
const runDetail = await getRunDetail(run_id);
```

### WebSocket Streaming
```typescript
// Real-time playback hook
const {
  status,
  playing,
  speed,
  play,
  pause,
  setSpeed
} = useRunPlayback(run_id);

// Subscribe to streaming frames
useEffect(() => {
  const unsubscribe = subscribe((frame) => {
    // Update charts with new data
    chartAPI.updateCandles(frame.ohlc);
    chartAPI.updateOrders(frame.orders);
  });
  return unsubscribe;
}, []);
```

## 📊 Chart Integration

### Candlestick Chart
```typescript
<ChartOHLC
  height={400}
  onReady={(api) => {
    // Store imperative API reference
    chartRef.current = api;
  }}
/>

// Update chart data
chartRef.current?.updateCandles(candleData);
chartRef.current?.updateOrders(orderData);
```

### Equity Chart
```typescript
<EquityChart
  height={300}
  onReady={(api) => {
    equityRef.current = api;
  }}
/>

// Update equity curve
equityRef.current?.updateEquity(equityPoints);
```

## 🧪 Testing

### Test Structure
- **Unit Tests**: Component logic and utility functions
- **Integration Tests**: API integration and data flow
- **Mock Services**: Isolated testing with mock data

### Running Tests
```bash
npm run test          # Run all tests
npm run test:watch    # Watch mode for development
npm run test:coverage # Generate coverage report
```

## 🎨 Styling Guidelines

### TailwindCSS Usage
- **Utility Classes**: Prefer utility classes over custom CSS
- **Responsive Design**: Mobile-first responsive breakpoints
- **Consistent Spacing**: Use Tailwind spacing scale (4, 8, 16, etc.)
- **Color Palette**: Stick to defined color scheme

### Component Styling
```typescript
// Good: Utility classes with consistent spacing
<div className="p-4 bg-white rounded-lg shadow-sm">
  <h2 className="text-lg font-semibold mb-2">Title</h2>
  <p className="text-gray-600">Content</p>
</div>
```

## 🔧 Development Guidelines

### Code Quality
- **ESLint**: Enforced code style and best practices
- **TypeScript**: Strict mode with comprehensive type checking
- **Prettier**: Consistent code formatting
- **Husky**: Pre-commit hooks for quality gates

### Performance Best Practices
- **React.memo**: Memoize expensive components
- **useCallback/useMemo**: Optimize re-renders
- **Code Splitting**: Lazy load routes and heavy components
- **Bundle Analysis**: Monitor bundle size and dependencies

### Error Handling
- **Error Boundaries**: Catch and display component errors gracefully
- **API Errors**: Consistent error handling with user-friendly messages
- **Loading States**: Clear feedback during async operations
- **Retry Logic**: Automatic retry for transient failures

## 🚀 Deployment

### Production Build
```bash
npm run build
```
Generates optimized static files in the `dist/` directory.

### Environment Configuration
- **Development**: Uses Vite proxy for API calls
- **Production**: Configure API base URL for your deployment
- **Environment Variables**: Use `.env` files for configuration

## 📚 Additional Resources

- **[Component Map](../docs/frontend/component-map.md)**: Detailed component architecture
- **[API Documentation](../docs/api/openapi.yaml)**: Backend API specification
- **[WebSocket Protocol](../docs/api/ws-protocol.md)**: Streaming protocol details
- **[Architecture Overview](../docs/architecture.md)**: System design documentation
