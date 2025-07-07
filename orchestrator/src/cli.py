#!/usr/bin/env python3
"""
Simplified CLI for orchestrator.
"""

import argparse
import os
from workflow import Workflow


class CLI:
    def __init__(self, data_scraper_url: str, image_downloader_url: str):
        self.workflow = Workflow(data_scraper_url, image_downloader_url)
    
    def trigger(self, trigger: str) -> None:
        """Trigger a workflow."""
        result = self.workflow.run(trigger)
        if result["status"] == "success":
            print(f"✅ Workflow completed: {result['html_file']}")
        else:
            print(f"❌ Workflow failed: {result['message']}")
    
    def status(self) -> None:
        """Show orchestrator status."""
        print("📊 Orchestrator Status")
        print("=" * 30)
        
        print(f"\n🔍 Services:")
        services_healthy = self.workflow.service_client.check_services_health()
        print(f"  Overall health: {'✅ Healthy' if services_healthy else '❌ Unhealthy'}")
        
        print(f"\n🎯 Workflow:")
        if self.workflow.is_running():
            print("  🟡 Running")
        else:
            print("  🟢 Idle")
        
        print(f"\n🎯 Supported Triggers:")
        print("  • wikipedia-animals")
    
    def run(self) -> None:
        """Run the CLI."""
        parser = argparse.ArgumentParser(description="Orchestrator CLI")
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        trigger_parser = subparsers.add_parser('trigger', help='Trigger a workflow')
        trigger_parser.add_argument('trigger', help='Trigger in format {source}-{category} (e.g., wikipedia-animals)')
        
        status_parser = subparsers.add_parser('status', help='Show orchestrator status')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        if args.command == 'trigger':
            self.trigger(args.trigger)
        elif args.command == 'status':
            self.status() 