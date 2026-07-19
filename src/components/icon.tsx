import type { SVGProps } from "react";

export type IconName =
  | "home" | "children" | "document" | "calendar" | "photo" | "settings"
  | "profile" | "logout" | "search" | "plus" | "arrow" | "check"
  | "clock" | "warning" | "drive" | "spark" | "download" | "edit"
  | "shield" | "menu" | "close" | "mail" | "phone" | "location"
  | "upload" | "heart" | "chevron" | "more";

const paths: Record<IconName, string[]> = {
  home: ["M3 10.8 12 3l9 7.8", "M5.5 9.5V21h13V9.5", "M9 21v-7h6v7"],
  children: ["M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2", "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "M22 21v-2a4 4 0 0 0-3-3.87", "M16 3.13a4 4 0 0 1 0 7.75"],
  document: ["M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z", "M14 2v6h6", "M8 13h8", "M8 17h6"],
  calendar: ["M3 5h18v16H3Z", "M16 3v4", "M8 3v4", "M3 10h18"],
  photo: ["M4 4h16v16H4Z", "m4 16 4-5 3 3 3-4 6 6", "M9 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z"],
  settings: ["M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z", "M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2 3.46-.08-.02a1.7 1.7 0 0 0-1.83.43l-.66.38a1.7 1.7 0 0 0-.83 1.71V23h-4v-.1a1.7 1.7 0 0 0-.83-1.71l-.66-.38a1.7 1.7 0 0 0-1.83-.43L7 20.4 5 16.94l.06-.06A1.7 1.7 0 0 0 5.4 15v-.76a1.7 1.7 0 0 0-1-1.54l-.08-.04V8.7l.08-.04a1.7 1.7 0 0 0 1-1.54v-.76a1.7 1.7 0 0 0-.34-1.88L5 4.42 7 1l.08.02a1.7 1.7 0 0 0 1.83-.43l.66-.38A1.7 1.7 0 0 0 10.4-1.5h3.2a1.7 1.7 0 0 0 .83 1.71l.66.38a1.7 1.7 0 0 0 1.83.43L17 1l2 3.46-.06.06a1.7 1.7 0 0 0-.34 1.88v.76a1.7 1.7 0 0 0 1 1.54l.08.04v3.92l-.08.04a1.7 1.7 0 0 0-1 1.54Z"],
  profile: ["M20 21a8 8 0 0 0-16 0", "M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"],
  logout: ["M10 17l5-5-5-5", "M15 12H3", "M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"],
  search: ["m21 21-4.35-4.35", "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z"],
  plus: ["M12 5v14", "M5 12h14"],
  arrow: ["M5 12h14", "m13 6 6 6-6 6"],
  check: ["m5 12 4 4L19 6"],
  clock: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z", "M12 6v6l4 2"],
  warning: ["M10.3 3.5 2 18h20L13.7 3.5a2 2 0 0 0-3.4 0Z", "M12 9v4", "M12 17h.01"],
  drive: ["m8 3-6 10 4 7h12l4-7-6-10Z", "M2 13h20", "m8 3 4 7 4-7"],
  spark: ["m12 3 1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7Z", "m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8Z"],
  download: ["M12 3v12", "m7 10 5 5 5-5", "M5 21h14"],
  edit: ["M12 20h9", "m16.5 3.5 4 4L8 20l-5 1 1-5Z"],
  shield: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z", "m9 12 2 2 4-4"],
  menu: ["M4 7h16", "M4 12h16", "M4 17h16"],
  close: ["m6 6 12 12", "M18 6 6 18"],
  mail: ["M3 5h18v14H3Z", "m3 7 9 6 9-6"],
  phone: ["M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7l.5 3.6a2 2 0 0 1-.6 1.7l-1.3 1.3a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 1.7-.6l3.6.5a2 2 0 0 1 1.7 2Z"],
  location: ["M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z", "M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"],
  upload: ["M12 16V4", "m7 9 5-5 5 5", "M5 20h14"],
  heart: ["M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"],
  chevron: ["m9 18 6-6-6-6"],
  more: ["M5 12h.01", "M12 12h.01", "M19 12h.01"]
};

export function Icon({ name, size = 20, ...props }: SVGProps<SVGSVGElement> & { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      {paths[name].map((path, index) => <path d={path} key={`${name}-${index}`} />)}
    </svg>
  );
}
