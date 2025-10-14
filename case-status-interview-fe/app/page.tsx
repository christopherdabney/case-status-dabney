import { Client } from "@/components/client";
import { type Client as ClientType } from "@/lib/definitions";

const fakeClient: ClientType = {
  id: 1,
  firm_id: 1,
  first_name: "John",
  last_name: "Doe",
  birth_date: new Date().toISOString(),
  email: "johndoe@example.com",
  cell_phone: "5555555555",
  integration_id: "integration-234",
  ssn: "123-45-6789",
};

export default async function Home() {
  return (
    <div className="flex flex-col w-full">
      <div className="flex flex-row justify-center">
        <h1 className="text-2xl font-bold">Clients</h1>
      </div>

      <div className="flex flex-row w-full">
        <ul className="w-full">
          <li className="w-full">
            <Client client={fakeClient} />
          </li>
        </ul>
      </div>
    </div>
  );
}
