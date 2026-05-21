
      // Protect this page - only admins can access
      if (!auth.requireAdmin(true)) {
        throw new Error("Access denied");
      }
    