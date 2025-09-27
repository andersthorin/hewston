# Epic 9 — Frontend BFF Integration

**Status**: Ready for Implementation  
**Priority**: High  
**Estimated Effort**: 1-2 weeks  
**Dependencies**: Epic 8 (BFF Implementation) - Complete ✅

## Epic Goal

Migrate the React frontend from direct backend API calls to use the BFF layer, reducing frontend complexity by 50%+ while maintaining feature flags for safe rollback capability.

## Why (Value)

- **Developer Productivity**: Simplify frontend API logic by using aggregated BFF endpoints
- **Performance Improvement**: Leverage BFF's data aggregation and caching for faster loading
- **System Maintainability**: Centralize data transformation logic in BFF layer
- **User Experience**: Faster chart loading and more reliable data operations
- **Risk Mitigation**: Feature flags enable instant rollback to direct backend calls

## Epic Description

### Existing System Context

- **Current Functionality:** React frontend directly calls FastAPI backend via Vite proxy (`/backtests`, `/bars/*`) using `frontend/src/services/api.ts`
- **Technology Stack:** React + TypeScript, Vite dev server, Zod validation, TanStack Query, existing API utilities
- **Integration Points:** API client (`frontend/src/services/api.ts`), Vite proxy config (`vite.config.ts`), constants file (`frontend/src/constants.ts`), WebSocket connections
- **Architecture Pattern:** Direct frontend-to-backend communication with client-side data transformation

### Enhancement Details

- **What's Being Changed:** Frontend API client configuration and endpoint URLs to use BFF (`http://127.0.0.1:8001`) instead of direct backend calls (`http://127.0.0.1:8000`)
- **How It Integrates:** Update API base URLs, implement feature flags for gradual migration, simplify data transformation logic in components (moved to BFF)
- **Technology Choice:** Maintain existing React + TypeScript patterns, add environment-based feature flags

### Success Criteria

- **Complexity Reduction:** 50% reduction in frontend API complexity through BFF aggregated endpoints
- **Performance Maintenance:** Improved chart loading times with BFF caching and aggregation
- **Zero Breaking Changes:** All existing functionality preserved during migration
- **Migration Safety:** Feature flags enable instant rollback to direct backend calls

## Scope

### In Scope

- **API Client Configuration:** Update frontend constants and API utilities to support BFF endpoints
- **Feature Flag Implementation:** Environment-based toggles for BFF vs direct backend selection
- **Component Migration:** Update chart and run detail components to use BFF aggregated endpoints
- **Data Transformation Simplification:** Remove client-side data transformation logic (moved to BFF)
- **WebSocket Integration:** Update WebSocket connections to use BFF proxy with enhanced reliability
- **Testing and Validation:** Comprehensive testing to ensure no functional regressions

### Out of Scope

- **React Component Changes:** No modifications to existing component interfaces or user experience
- **Backend Modifications:** No changes to existing FastAPI backend service (Epic 8 complete)
- **Database Schema Changes:** No database modifications required
- **New Frontend Features:** Focus purely on BFF integration, not new business functionality
- **UI/UX Changes:** No modifications to existing user interfaces or workflows

## Stories

### Story 9.1: API Client Configuration and Feature Flags
**Effort**: 1-2 days  
**Dependencies**: None (Epic 8 complete)

**User Story**: As a developer, I want configurable API endpoints with feature flags, so that I can safely migrate from direct backend calls to BFF endpoints with rollback capability.

**Key Deliverables**:
- Update `frontend/src/constants.ts` to support BFF URLs with environment variables
- Implement feature flags in API client for BFF vs backend endpoint selection
- Update Vite proxy configuration to route BFF calls appropriately
- Environment-based configuration for gradual migration control

### Story 9.2: Frontend Component Migration
**Effort**: 2-3 days
**Dependencies**: Story 9.1

**User Story**: As a trader, I want faster chart loading and simplified data operations, so that I can analyze market data more efficiently through the BFF layer.

**Key Deliverables**:
- Migrate chart components to use BFF `/api/v1/chart-data` endpoint
- Update run detail components to use `/api/v1/runs/{id}/complete` aggregated endpoint
- Simplify data transformation logic in components (logic moved to BFF)
- Update TypeScript types for BFF response formats

### Story 9.3: WebSocket Integration and Validation
**Effort**: 1-2 days
**Dependencies**: Story 9.2

**User Story**: As a trader, I want reliable real-time streaming through the BFF proxy, so that I can watch strategy execution with enhanced connection management.

**Key Deliverables**:
- Update WebSocket connections to use BFF proxy (`/api/v1/runs/{id}/stream`)
- Comprehensive regression testing to ensure no functional changes
- Performance validation comparing BFF vs direct backend performance
- Feature flag testing and rollback verification

## Dependencies

### Technical Dependencies
- **Epic 8 Complete**: BFF service fully implemented and operational (✅ Complete)
- **Frontend Stability**: React frontend must remain stable during migration
- **Environment Configuration**: Support for environment-based feature flags
- **Testing Infrastructure**: Existing frontend testing framework for regression validation

### Team Dependencies
- **Frontend Team**: Execute API client migration and component updates
- **QA Team**: Validate integration and performance testing
- **DevOps Team**: Support environment configuration and deployment coordination

## Risks & Mitigation

### Technical Risks

1. **Integration Complexity** (Low-Medium Risk)
   - **Risk**: Frontend migration introduces unexpected compatibility issues
   - **Mitigation**: Feature flags enable endpoint-by-endpoint migration and instant rollback
   - **Monitoring**: Comprehensive regression testing and performance monitoring

2. **Performance Impact** (Low Risk)
   - **Risk**: BFF integration affects frontend performance
   - **Mitigation**: BFF designed for performance improvement with caching and aggregation
   - **Validation**: Performance testing comparing BFF vs direct backend calls

### Operational Risks

1. **Migration Coordination** (Low Risk)
   - **Risk**: Frontend migration affects development workflow
   - **Mitigation**: Feature flags allow gradual migration without disrupting development
   - **Safety**: Instant rollback capability through environment variables

## Success Metrics

### Technical Metrics
- **API Complexity Reduction**: 50% fewer API calls from frontend through BFF aggregation
- **Performance Improvement**: Chart data loading within 2 seconds (improved from current)
- **Error Handling**: 100% of existing error scenarios handled correctly through BFF
- **Feature Flag Coverage**: 100% rollback capability for all migrated endpoints

### Developer Experience Metrics
- **Development Speed**: Faster feature development with simplified API patterns
- **Code Quality**: Reduced complexity in frontend data transformation logic
- **Debugging Efficiency**: Improved error tracking through BFF correlation IDs
- **Maintainability**: Single source of truth for API patterns in BFF layer

### User Experience Metrics
- **Loading Performance**: Consistent and improved chart loading times
- **Error Recovery**: Maintained error handling and user feedback
- **Connection Stability**: Enhanced WebSocket reliability through BFF proxy
- **Data Consistency**: Uniform data formats from BFF aggregation

## Definition of Done

### Technical Completion
- [ ] All 3 stories completed with acceptance criteria met
- [ ] Frontend successfully uses BFF for all data operations
- [ ] Feature flags functional for safe rollback to direct backend
- [ ] Chart loading performance improved through BFF aggregation
- [ ] WebSocket connections use BFF proxy with enhanced reliability

### Quality Assurance
- [ ] Comprehensive regression testing verifies existing functionality
- [ ] Integration tests validate frontend-BFF communication
- [ ] Performance testing confirms improvement over direct backend calls
- [ ] Feature flag testing validates rollback capabilities
- [ ] End-to-end testing confirms complete user workflows

### Production Readiness
- [ ] Environment configuration supports BFF endpoint selection
- [ ] Monitoring configured for frontend-BFF integration performance
- [ ] Documentation updated with new API client patterns
- [ ] Team training completed on feature flag usage and rollback procedures

---

**Epic Owner**: Sarah (Product Owner)  
**Technical Lead**: TBD  
**Implementation Priority**: High (completes BFF integration)  
**Architecture Reference**: [`docs/architecture/bff-architecture.md`](../architecture/bff-architecture.md)
