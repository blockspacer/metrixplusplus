#
#    Metrix++, Copyright 2009-2013, Metrix++ Project
#    Link: http://metrixplusplus.sourceforge.net
#    
#    This file is a part of Metrix++ Tool.
#    
#    Metrix++ is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#    
#    Metrix++ is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with Metrix++.  If not, see <http://www.gnu.org/licenses/>.
#


import mpp.api
import mpp.utils

class Plugin(mpp.api.Plugin, mpp.api.IConfigurable, mpp.api.IRunable):
    
    def declare_configuration(self, parser):
        parser.add_option("--format", "--ft", default='xml', choices=['txt', 'xml', 'python'], help="Format of the output data. "
                          "Possible values are 'xml', 'txt' or 'python' [default: %default]")
        parser.add_option("--nest-regions", "--nr", action="store_true", default=False,
                          help="If the option is set (True), data for regions is exported in the form of a tree. "
                          "Otherwise, all regions are exported in plain list. [default: %default]")
    
    def configure(self, options):
        self.out_format = options.__dict__['format']
        self.nest_regions = options.__dict__['nest_regions']

    def run(self, args):
        loader_prev = self.get_plugin_loader().get_plugin('mpp.dbf').get_loader_prev()
        loader = self.get_plugin_loader().get_plugin('mpp.dbf').get_loader()
    
        paths = None
        if len(args) == 0:
            paths = [""]
        else:
            paths = args
        
        (result, exit_code) = export_to_str(self.out_format, paths, loader, loader_prev, self.nest_regions)
        print result
        return exit_code

def export_to_str(out_format, paths, loader, loader_prev, nest_regions):
    exit_code = 0
    result = ""
    if out_format == 'txt':
        result += "=" * 80 + "\n" + "Export" + "\n" + "_" * 80 + "\n\n"
    elif out_format == 'xml':
        result += "<export>\n"
    elif out_format == 'python':
        result += "{'export': ["

    for (ind, path) in enumerate(paths):
        path = mpp.utils.preprocess_path(path)
        
        aggregated_data = loader.load_aggregated_data(path)
        aggregated_data_tree = {}
        subdirs = []
        subfiles = []
        if aggregated_data != None:
            aggregated_data_tree = aggregated_data.get_data_tree()
            subdirs = aggregated_data.get_subdirs()
            subfiles = aggregated_data.get_subfiles()
        else:
            mpp.utils.report_bad_path(path)
            exit_code += 1
        aggregated_data_prev = loader_prev.load_aggregated_data(path)
        if aggregated_data_prev != None:
            aggregated_data_tree = append_diff(aggregated_data_tree,
                                           aggregated_data_prev.get_data_tree())
        
        file_data = loader.load_file_data(path)
        file_data_tree = {}
        if file_data != None:
            file_data_tree = file_data.get_data_tree() 
            file_data_prev = loader_prev.load_file_data(path)
            append_regions(file_data_tree, file_data, file_data_prev, nest_regions)
        
        data = {"info": {"path": path, "id": ind + 1},
                "aggregated-data": aggregated_data_tree,
                "file-data": file_data_tree,
                "subdirs": subdirs,
                "subfiles": subfiles}

        if out_format == 'txt':
            result += mpp.utils.serialize_to_txt(data, root_name = "data") + "\n"
            #cout_txt(data)
        elif out_format == 'xml':
            result += mpp.utils.serialize_to_xml(data, root_name = "data") + "\n"
        elif out_format == 'python':
            postfix = ""
            if ind < len(paths) - 1:
                postfix = ", "
            result += mpp.utils.serialize_to_python(data, root_name = "data") + postfix

    if out_format == 'txt':
        result += "\n"
    elif out_format == 'xml':
        result += "</export>"
    elif out_format == 'python':
        result += "]}"
        
    return (result, exit_code)

def append_regions(file_data_tree, file_data, file_data_prev, nest_regions):
    regions_matcher = None
    if file_data_prev != None:
        file_data_tree = append_diff(file_data_tree,
                                     file_data_prev.get_data_tree())
        regions_matcher = mpp.utils.FileRegionsMatcher(file_data, file_data_prev)
    
    if nest_regions == False:
        regions = []
        for region in file_data.iterate_regions():
            region_data_tree = region.get_data_tree()
            if regions_matcher != None and regions_matcher.is_matched(region.get_id()):
                region_data_prev = file_data_prev.get_region(regions_matcher.get_prev_id(region.get_id()))
                region_data_tree = append_diff(region_data_tree,
                                               region_data_prev.get_data_tree())
            regions.append({"info": {"name" : region.name,
                                     'type' : file_data.get_region_types()().to_str(region.get_type()),
                                     "cursor" : region.cursor,
                                     'line_begin': region.line_begin,
                                     'line_end': region.line_end,
                                     'offset_begin': region.begin,
                                     'offset_end': region.end},
                            "data": region_data_tree})
        file_data_tree['regions'] = regions
    else:
        def append_rec(region_id, file_data_tree, file_data, file_data_prev):
            region = file_data.get_region(region_id)
            region_data_tree = region.get_data_tree()
            if regions_matcher != None and regions_matcher.is_matched(region.get_id()):
                region_data_prev = file_data_prev.get_region(regions_matcher.get_prev_id(region.get_id()))
                region_data_tree = append_diff(region_data_tree,
                                               region_data_prev.get_data_tree())
            result = {"info": {"name" : region.name,
                               'type' : file_data.get_region_types()().to_str(region.get_type()),
                               "cursor" : region.cursor,
                               'line_begin': region.line_begin,
                               'line_end': region.line_end,
                               'offset_begin': region.begin,
                               'offset_end': region.end},
                      "data": region_data_tree,
                      "subregions": []}
            for sub_id in file_data.get_region(region_id).iterate_subregion_ids():
                result['subregions'].append(append_rec(sub_id, file_data_tree, file_data, file_data_prev))
            return result
        file_data_tree['regions'] = []
        file_data_tree['regions'].append(append_rec(1, file_data_tree, file_data, file_data_prev))

def append_diff(main_tree, prev_tree):
    assert(main_tree != None)
    assert(prev_tree != None)
    
    for name in main_tree.keys():
        if name not in prev_tree.keys():
            continue
        for field in main_tree[name].keys():
            if field not in prev_tree[name].keys():
                continue
            if isinstance(main_tree[name][field], dict) and isinstance(prev_tree[name][field], dict):
                diff = {}
                for key in main_tree[name][field].keys():
                    if key not in prev_tree[name][field].keys():
                        continue
                    main_val = main_tree[name][field][key]
                    prev_val = prev_tree[name][field][key]
                    if main_val == None:
                        main_val = 0
                    if prev_val == None:
                        prev_val = 0
                    if isinstance(main_val, list) and isinstance(prev_val, list):
                        main_tree[name][field][key] = append_diff_list(main_val, prev_val)
                    else:
                        diff[key] = main_val - prev_val
                main_tree[name][field]['__diff__'] = diff
            elif (not isinstance(main_tree[name][field], dict)) and (not isinstance(prev_tree[name][field], dict)):
                if '__diff__' not in main_tree[name]:
                    main_tree[name]['__diff__'] = {}
                main_tree[name]['__diff__'][field] = main_tree[name][field] - prev_tree[name][field]
    return main_tree

def append_diff_list(main_list, prev_list):
    merged_list = {}
    for bar in main_list:
        merged_list[bar['metric']] = {'count': bar['count'], '__diff__':0, 'ratio': bar['ratio']}
    for bar in prev_list:
        if bar['metric'] in merged_list.keys():
            merged_list[bar['metric']]['__diff__'] = \
                merged_list[bar['metric']]['count'] - bar['count']
        else:
            merged_list[bar['metric']] = {'count': 0, '__diff__':-bar['count'], 'ratio': bar['ratio']}
    result = []
    for metric in sorted(merged_list.keys()):
        result.append({'metric':metric,
                       'count':merged_list[metric]['count'],
                       'ratio':merged_list[metric]['ratio'],
                       '__diff__':merged_list[metric]['__diff__']})
    return result

def cout_txt_regions(regions, indent = 0):
    print indent, "dumping regions"
    for region in regions:
        print indent, 'region:', region['info']
        for namespace in region['data'].keys():
            diff_data = {}
            if '__diff__' in region['data'][namespace].keys():
                diff_data = region['data'][namespace]['__diff__']
            for field in region['data'][namespace].keys():
                diff_str = ""
                if field == '__diff__':
                    continue
                if field in diff_data.keys():
                    diff_str = "[" + ("+" if diff_data[field] >= 0 else "") + str(diff_data[field]) + "]"
                print indent, namespace, field, region['data'][namespace][field], diff_str
        if 'subregions' in region.keys():
            cout_txt_regions(region['subregions'], indent=indent+1)

def cout_txt(data):
    print "FILE DATA"
    for key in data['file-data'].keys():
        if key == 'regions':
            cout_txt_regions(data['file-data'][key])
        else:
            print "dumping per file data"
            namespace = key
            diff_data = {}
            if '__diff__' in data['file-data'][namespace].keys():
                diff_data = data['file-data'][namespace]['__diff__']
            for field in data['file-data'][namespace].keys():
                diff_str = ""
                if field == '__diff__':
                    continue
                if field in diff_data.keys():
                    diff_str = "[" + ("+" if diff_data[field] >= 0 else "") + str(diff_data[field]) + "]"
                print namespace, field, data['file-data'][namespace][field], diff_str
    print "AGGREGATED DATA"
    for namespace in data['aggregated-data'].keys():
        for field in data['aggregated-data'][namespace].keys():
            diff_data = {}
            if '__diff__' in data['aggregated-data'][namespace][field].keys():
                diff_data = data['aggregated-data'][namespace][field]['__diff__']
            for attr in data['aggregated-data'][namespace][field].keys():
                diff_str = ""
                if attr == 'distribution-bars' or attr == '__diff__':
                    continue
                if attr in diff_data.keys():
                    diff_str = "[" + ("+" if diff_data[attr] >= 0 else "") + str(diff_data[attr]) + "]"
                print namespace, field, attr, data['aggregated-data'][namespace][field][attr], diff_str
            for bar in data['aggregated-data'][namespace][field]['distribution-bars']:
                diff_str = ""
                if '__diff__' in bar.keys():
                    diff_str = "[" + ("+" if bar['__diff__'] >= 0 else "") + str(bar['__diff__']) + "]"
                print "bar:", '|'*int(round(bar['ratio']*100)), bar['ratio'], bar['count'], bar['metric'], diff_str 
    