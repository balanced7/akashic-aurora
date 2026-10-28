import { useQuery } from "@tanstack/react-query";

import { billing } from "~/modules/billing/lib/api";

export const useCustomer = () => useQuery(billing.queries.customer.get);
