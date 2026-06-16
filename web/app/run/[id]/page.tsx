// Server component wrapper for the dynamic /run/[id] route.
//
// Static export (output: "export", used on Render) requires every dynamic
// route to declare its params at build time. Run IDs are UUIDs created at
// runtime, so there are none to pre-render — we emit a single shell page and
// let the client component (RunResults) read the ID from the URL and poll the
// API in the browser. `generateStaticParams` must live in a server component,
// which is why the UI is split out into RunResults.tsx ("use client").
import RunResults from "./RunResults";

export function generateStaticParams() {
  return [{ id: "_" }];
}

export const dynamicParams = false;

export default function Page() {
  return <RunResults />;
}
