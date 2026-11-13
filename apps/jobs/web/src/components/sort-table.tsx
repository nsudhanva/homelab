import { useTable, type ColumnDef, type RowData, type SortingState } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import { features, type Features } from "@/lib/table";
import { cn } from "@/lib/utils";

type Props<T extends RowData> = {
  data: T[];
  columns: ColumnDef<Features, T, any>[];
  sorting: SortingState;
  rowKey: (row: T) => string;
  expanded?: string | null;
  onRowClick?: (row: T) => void;
  renderExpanded?: (row: T) => ReactNode;
};

export function SortTable<T extends RowData>({ data, columns, sorting, rowKey, expanded, onRowClick, renderExpanded }: Props<T>) {
  const table = useTable({
    features,
    columns,
    data,
    getRowId: rowKey,
    initialState: { sorting },
    enableSortingRemoval: false,
  });
  const width = columns.length;
  return (
    <div className="overflow-x-auto rounded-xl border bg-card">
      <table className="w-full border-separate border-spacing-0 text-sm">
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((header) => {
                const sorted = header.column.getIsSorted();
                const Icon = sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ArrowUpDown;
                return (
                  <th key={header.id} className="border-b px-3 py-2.5 text-left text-xs font-medium whitespace-nowrap text-muted-foreground">
                    {header.column.getCanSort() ? (
                      <button
                        type="button"
                        onClick={header.column.getToggleSortingHandler()}
                        className={cn("inline-flex items-center gap-1 hover:text-foreground", sorted && "text-foreground")}
                      >
                        <table.FlexRender header={header} />
                        <Icon className={cn("size-3", !sorted && "opacity-40")} />
                      </button>
                    ) : (
                      <table.FlexRender header={header} />
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => {
            const open = expanded === row.id;
            return (
              <Fragment key={row.id}>
                <tr
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  className={cn(onRowClick && "cursor-pointer hover:bg-accent/50", open && "bg-accent/40")}
                >
                  {row.getAllCells().map((cell) => (
                    <td key={cell.id} className="border-b px-3 py-2.5 align-top">
                      <table.FlexRender cell={cell} />
                    </td>
                  ))}
                </tr>
                {open && renderExpanded && (
                  <tr>
                    <td colSpan={width} className="border-b bg-muted/40 px-3 py-3">
                      {renderExpanded(row.original)}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
      {data.length === 0 && <p className="py-10 text-center text-sm text-muted-foreground">Nothing matches.</p>}
    </div>
  );
}
