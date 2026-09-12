import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title:'MetroAI · Houston journey planner',description:'Plan Houston transit journeys with actual METRO schedules and current service alerts.',icons:{icon:'/favicon.svg'}};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
