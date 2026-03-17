import React from "react";

type Scope = { user_id: string; course_id: string; activity_id: string };

type XplActivityProps = {
  scope: Scope;
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
          "data-scope"?: string;
          "data-state"?: string;
          "data-permission"?: string;
          "data-src"?: string;
        },
        HTMLElement
      >;
    }
  }
}

export function XplActivity({ scope, clientPath, state, permission }: XplActivityProps) {
  return (
    <xpl-activity
      data-scope={JSON.stringify(scope)}
      data-state={JSON.stringify(state)}
      data-permission={permission}
      data-src={`/a/${scope.activity_id}/${clientPath}`}
    />
  );
}
