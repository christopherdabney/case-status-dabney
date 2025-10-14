import { type Client } from "@/lib/definitions";

export function Client({ client }: { client: Client }) {
  return (
    <div className="border-2 border-gray-100 w-full px-4 py-1 flex flex-col gap-2">
      <div className="flex flex-row gap-2 items-center">
        <h3 className="font-semibold">{`${client.first_name} ${client.last_name}`}</h3>
        <h3 className="font-extralight text-sm">({client.ssn})</h3>
      </div>
      <div className="flex flex-row justify-between">
        <p className="font-light text-md">{client.cell_phone}</p>
        <p className="font-light text-md">{client.email}</p>
        <p className="font-light text-md">{client.birth_date}</p>
      </div>
    </div>
  );
}
