// Compute New York trading day key 'YYYY-MM-DD' from an ISO timestamp string
export function nyBusinessDayKey(isoTs: string): string {
  const d = new Date(isoTs)
  // Use en-CA to get zero-padded YYYY-MM-DD reliably
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(d)
}

