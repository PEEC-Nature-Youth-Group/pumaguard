/// Stub implementation for non-web platforms (VM, tests, etc.).
///
/// This provides a default localhost URL for testing and non-web environments
/// where browser APIs are not available.
library;

String getApiBaseUrl() {
  // Default to localhost for test environments
  // In a real production non-web build, this would need proper configuration
  return 'http://localhost:5000';
}
