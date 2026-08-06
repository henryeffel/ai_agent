import React from "react";
import { Box, Button, VStack } from "@chakra-ui/react";
import { useLocation, useNavigate } from "react-router-dom";
import { FiHome, FiSettings } from "react-icons/fi";

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const items = [
    { label: "Agent Demo", icon: FiHome, path: "/home" },
    { label: "설정", icon: FiSettings, path: "/settings" },
  ];
  return (
    <Box w="200px" bg="white" borderRight="1px solid" borderColor="gray.200" p={4}>
      <VStack spacing={2} align="stretch">
        {items.map((item) => (
          <Button key={item.path} leftIcon={<item.icon />} variant={location.pathname === item.path ? "solid" : "ghost"} colorScheme={location.pathname === item.path ? "purple" : "gray"} justifyContent="flex-start" onClick={() => navigate(item.path)}>
            {item.label}
          </Button>
        ))}
      </VStack>
    </Box>
  );
}
