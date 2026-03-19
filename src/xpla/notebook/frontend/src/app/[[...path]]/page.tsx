import { ClientRouter } from "./client-router";

export function generateStaticParams() {
  return [{ path: [] }];
}

export default function CatchAllPage() {
  return <ClientRouter />;
}
