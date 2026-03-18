import React from "react";

type Context = { user_id: string; course_id: string; activity_id: string };

type XplActivityProps = {
  context: Context;
  clientPath: string;
  state: unknown;
  permission: string;
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace React.JSX {
    interface IntrinsicElements {
      "xpl-activity": React.DetailedHTMLProps<
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

export function XplActivity({ context, clientPath, state, permission }: XplActivityProps) {
  return (
    <xpl-activity
      data-context={JSON.stringify(context)}
      data-state={JSON.stringify(state)}
      data-permission={permission}
      data-src={`/a/${context.activity_id}/${clientPath}`}
    />
  );
}
