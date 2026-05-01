import React from "react";

type Context = { user_id: string; course_id: string; activity_id: string };

type PxcActivityProps = {
  context: Context;
  state: unknown;
  permission: string;
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace React.JSX {
    interface IntrinsicElements {
      "pxc-activity": React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          "data-context"?: string;
          "data-state"?: string;
          "data-permission"?: string;
          "data-src"?: string;
        },
        HTMLElement
      >;
    }
  }
}

export function PxcActivity({ context, state, permission }: PxcActivityProps) {
  return (
    <pxc-activity
      data-context={JSON.stringify(context)}
      data-state={JSON.stringify(state)}
      data-permission={permission}
      data-src={`/a/${context.activity_id}/ui.js`}
    />
  );
}
