"use client";

import * as React from "react";

import { cn } from "@akashic-labs/ui";
import { useBreakpoint } from "@akashic-labs/ui-web";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "#components/dialog";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "#components/drawer";

interface BaseProps {
  children: React.ReactNode;
}

interface RootModalProps extends BaseProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

interface ModalProps extends BaseProps {
  className?: string;
  asChild?: true;
}

const ModalContext = React.createContext<{ isDesktop: boolean }>({
  isDesktop: false,
});

const useModalContext = () => {
  const context = React.useContext(ModalContext);
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
  if (!context) {
    throw new Error(
      "Modal components cannot be rendered outside the Modal Context",
    );
  }
  return context;
};

const Modal = ({ children, ...props }: RootModalProps) => {
  const isDesktop = useBreakpoint("md");
  const ModalComponent = isDesktop ? Dialog : Drawer;

  return (
    <ModalContext.Provider value={{ isDesktop }}>
      <ModalComponent {...props} {...(isDesktop && { autoFocus: true })}>
        {children}
      </ModalComponent>
    </ModalContext.Provider>
  );
};

const ModalTrigger = ({ className, children, ...props }: ModalProps) => {
  const { isDesktop } = useModalContext();
  const ModalTriggerComponent = isDesktop ? DialogTrigger : DrawerTrigger;

  return (
    <ModalTriggerComponent className={className} {...props}>
      {children}
    </ModalTriggerComponent>
  );
};

const ModalClose = ({ className, children, ...props }: ModalProps) => {
  const { isDesktop } = useModalContext();
  const ModalCloseComponent = isDesktop ? DialogClose : DrawerClose;

  return (
    <ModalCloseComponent className={className} {...props}>
      {children}
    </ModalCloseComponent>
  );
};

const ModalContent = ({ className, children, ...props }: ModalProps) => {
  const { isDesktop } = useModalContext();
  const ModalContentComponent = isDesktop ? DialogContent : DrawerContent;

  return (
    <ModalContentComponent className={className} {...props}>
      {children}
    </ModalContentComponent>
  );
};

const ModalDescription = ({ className, children, ...props }: ModalProps) => {
  const { isDesktop } = useModalContext();
  const ModalDescriptionComponent = isDesktop
    ? DialogDescription
    : DrawerDescription;

  return (
    <ModalDescriptionComponent className={className} {...props}>
      {children}
    </ModalDescriptionComponent>
  );
};

const ModalHeader = ({ className, children, ...props }: ModalProps) => {
  const { isDesktop } = useModalContext();
  const ModalHeaderComponent = isDesktop ? DialogHeader : DrawerHeader;

  return (
    <ModalHeaderComponent className={className} {...props}>
      {children}
    </ModalHeaderComponent>
  );
};

const ModalTitle = ({ className, children, ...props }: ModalProps) => {
  const { isDesktop } = useModalContext();
  const ModalTitleComponent = isDesktop ? DialogTitle : DrawerTitle;

  return (
    <ModalTitleComponent className={className} {...props}>
      {children}
    </ModalTitleComponent>
  );
};

const ModalBody = ({ className, children, ...props }: ModalProps) => {
  return (
    <div className={cn("px-4 md:px-0", className)} {...props}>
      {children}
    </div>
  );
};

const ModalFooter = ({ className, children, ...props }: ModalProps) => {
  const { isDesktop } = useModalContext();
  const ModalFooterComponent = isDesktop ? DialogFooter : DrawerFooter;

  return (
    <ModalFooterComponent className={className} {...props}>
      {children}
    </ModalFooterComponent>
  );
};

export {
  Modal,
  ModalTrigger,
  ModalClose,
  ModalContent,
  ModalDescription,
  ModalHeader,
  ModalTitle,
  ModalBody,
  ModalFooter,
};
