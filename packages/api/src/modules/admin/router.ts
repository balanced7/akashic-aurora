import { Hono } from "hono";

import { enforceAdmin, enforceAuth } from "../../middleware";

import { getCustomersCount } from "./customers/queries";
import { customersRouter } from "./customers/router";
import { getOrganizationsCount } from "./organizations/queries";
import { organizationsRouter } from "./organizations/router";
import { getUsersCount } from "./users/queries";
import { usersRouter } from "./users/router";

export const adminRouter = new Hono()
  .use(enforceAuth)
  .use(enforceAdmin)
  .route("/users", usersRouter)
  .route("/organizations", organizationsRouter)
  .route("/customers", customersRouter)
  .get("/summary", async (c) => {
    const [users, organizations, customers] = await Promise.all([
      getUsersCount(),
      getOrganizationsCount(),
      getCustomersCount(),
    ]);

    return c.json({ users, organizations, customers });
  });
