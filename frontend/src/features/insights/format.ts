// No timeZone option, so buckets show in the browser's local time, like the event stream.
const bucketLabelFormatter = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
})
const bucketTooltipFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatBucketLabel(bucket: string) {
  return bucketLabelFormatter.format(new Date(bucket))
}

export function formatBucketTooltip(bucket: string) {
  return bucketTooltipFormatter.format(new Date(bucket))
}
